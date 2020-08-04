# -*- coding: utf-8 -*-
"""
Anonymisation support for Django ModelAdmin classes
"""
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from datetime import timedelta

from django.conf.urls import url
from django.contrib import admin
from django.contrib import messages
from django.forms import ChoiceField, Select, DateField
from django.forms import ModelForm
from django.forms.widgets import SelectDateWidget
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from ..models import PrivacyManager
from ..models import EventLog
from ..models import RetentionPolicyItem

try:
    from django.urls import reverse  # NOQA
except ImportError:
    # Django <2.0
    from django.core.urlresolvers import reverse

from .. import app_settings


class ModelAdmin(admin.ModelAdmin):
    anonymise_template = 'gdpr_assist/admin/action_anonymise.html'

    def get_actions(self, request):
        actions = super(ModelAdmin, self).get_actions(request)
        if getattr(self.model, app_settings.GDPR_PRIVACY_INSTANCE_NAME):
            actions['anonymise'] = (
                self.anonymise_action,
                'anonymise',
                'Anonymise data',
            )
        return actions

    def anonymise_action(self, modeladmin, request, queryset):
        selected = request.POST.getlist(admin.ACTION_CHECKBOX_NAME)
        return HttpResponseRedirect(
            '{url}?ids={ids}'.format(
                url=reverse(
                    'admin:{}_{}_anonymise'.format(
                        self.model._meta.app_label,
                        self.model._meta.model_name,
                    )
                ),
                ids=",".join(selected),
            )
        )

    def get_urls(self):
        urls = super(ModelAdmin, self).get_urls()
        extra_urls = [
            url(
                r'^anonymise/$',
                self.admin_site.admin_view(self.anonymise_view),
                name='{}_{}_anonymise'.format(
                    self.model._meta.app_label,
                    self.model._meta.model_name,
                ),
            ),
        ]
        return extra_urls + urls

    def perform_anonymisation(self, request, objects):
        """Performs anonymisation on the queryset.

        This might take a long time and timeout.
        This is a good place to use a taks instead.
        """
        objects.anonymise(user=request.user)

    def success_message(self, request, verbose_name, count):
        messages.success(
            request,
            "{} {} anonymised".format(count, verbose_name),
        )

    def anonymise_view(self, request):
        ids_raw = (request.POST or request.GET).get('ids')

        manager = self.model._meta.default_manager
        if not isinstance(manager, PrivacyManager):
            manager = PrivacyManager._cast_class(manager)

        objects = manager.filter(pk__in=ids_raw.split(','))
        verbose_name = (
            self.model._meta.verbose_name.title()
            if len(objects) == 1 else
            self.model._meta.verbose_name_plural.title()
        )
        changelist_url = reverse(
            'admin:{}_{}_changelist'.format(
                self.model._meta.app_label,
                self.model._meta.model_name,
            ),
        )

        if request.POST:
            self.perform_anonymisation(request, objects)
            count = objects.count()
            self.success_message(request, verbose_name, count)
            return HttpResponseRedirect(changelist_url)

        tree_html = ""

        tree = self.model.get_anonymisation_tree(objs=objects).replace(" [set_field]", "").replace(" [fk]", "")
        this_html = "{model_name}:\n{tree}\n\n".format(model_name=self.model.__name__, tree=tree)
        if self.model.__name__ != "RetentionPolicyItem":
            this_html = "<pre>{html}</pre>".format(html=this_html)
        tree_html += this_html

        tree_html = mark_safe(tree_html)

        return TemplateResponse(request, self.anonymise_template, {
            'title': _("Are you sure?"),
            'ids': ids_raw,
            'verbose_name': verbose_name,
            'objects': objects,
            'cancel_url': changelist_url,
            'trees': tree_html
        })


@admin.register(EventLog)
class EventLogAdmin(admin.ModelAdmin):
    readonly_fields = ["event", "app_label", "model_name", "target_pk", "acting_user"]
    list_display = ["summary", "log_time", "event", "app_label", "model_name", "target_pk", "acting_user"]
    list_filter = ["log_time", "acting_user", "app_label", "model_name", "event"]


class RetentionPolicyItemForm(ModelForm):
    DURATION_CHOICES = [(str(timedelta(days=days)), days) for days in range(100)]

    policy_length = ChoiceField(
        widget=Select(), choices=DURATION_CHOICES, required=True,
        help_text="Days before the associated record will be anonymised.")

    start_date = DateField(
        widget=SelectDateWidget(), required=True, initial=timezone.now,
        help_text="Change the start date of this policy.")

    class Meta:
        model = RetentionPolicyItem
        exclude = []


@admin.register(RetentionPolicyItem)
class RetentionPolicyItemAdmin(ModelAdmin):
    readonly_fields = ["updated_at", "get_anonymisation_log_formatted"]
    list_display = ["get_description", "anonymised", "start_date", "updated_at", "policy_length", "get_related_objects"]

    def get_anonymisation_log_formatted(self, obj):
        log = obj.get_anonymisation_log()
        if not log:
            return "[This retention policy has not yet been anonymised]"

        return mark_safe("<pre>{log}</pre>".format(log=log))

    get_anonymisation_log_formatted.short_description = "Anonymisation Log"

    def get_description(self, obj):
        return obj.description or "[No description]"
    get_description.short_description = "Description"

    def get_related_objects(self, obj):
        related_objects = obj.list_related_objects()

        related_objects_lis = [
            "<li><a href='{admin_url}'>{related_object}</a></li>".format(
                admin_url=reverse(
                    "admin:{}_{}_change".format(
                        related_object._meta.app_label,
                        related_object._meta.model_name,
                    ),
                    args=[related_object.pk]
                ),
                related_object=related_object,
            )
            for related_object in related_objects[:10]
        ]

        return mark_safe(
            "<ul>{lis}</ul>{elipse}".format(
                lis="\n".join(related_objects_lis),
                elipse="..." if len(related_objects) > 10 else "",
            )
        )
    get_related_objects.short_description = "Related objects with policy"

    form = RetentionPolicyItemForm
