"""
Anonymisation support for Django ModelAdmin classes
"""
from django.conf.urls import url
from django.contrib import admin
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.utils.translation import ugettext_lazy as _

try:
    from django.urls import reverse
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

    def anonymise_view(self, request):
        ids_raw = (request.POST or request.GET).get('ids')
        objects = self.model.objects.filter(pk__in=ids_raw.split(','))
        verbose_name = (
            self.model._meta.verbose_name.title()
            if objects.count() == 1 else
            self.model._meta.verbose_name_plural.title()
        )
        changelist_url = reverse(
            'admin:{}_{}_changelist'.format(
                self.model._meta.app_label,
                self.model._meta.model_name,
            ),
        )

        if request.POST:
            objects.anonymise()
            count = objects.count()
            messages.success(
                request,
                "{} {} anonymised".format(count, verbose_name),
            )
            return HttpResponseRedirect(changelist_url)

        return TemplateResponse(request, self.anonymise_template, {
            'title': _("Are you sure?"),
            'ids': ids_raw,
            'verbose_name': verbose_name,
            'objects': objects,
            'cancel_url': changelist_url,
        })
