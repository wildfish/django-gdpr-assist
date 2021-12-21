"""
Anonymisation support for Django ModelAdmin classes
"""
import django
from django.urls import re_path
from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .. import app_settings


if django.VERSION < (3, 1):
    from django.contrib.admin import ACTION_CHECKBOX_NAME
else:
    from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME


class ModelAdmin(admin.ModelAdmin):
    anonymise_template = "gdpr_assist/admin/action_anonymise.html"

    def get_actions(self, request):
        actions = super(ModelAdmin, self).get_actions(request)
        if (
            getattr(self.model, app_settings.GDPR_PRIVACY_INSTANCE_NAME)
            and self.model.check_can_anonymise()
        ):
            actions["anonymise"] = (
                self.anonymise_action,
                "anonymise",
                "Anonymise data",
            )
        return actions

    def anonymise_action(self, modeladmin, request, queryset):
        selected = request.POST.getlist(ACTION_CHECKBOX_NAME)
        return HttpResponseRedirect(
            "{url}?ids={ids}".format(
                url=reverse(
                    "admin:{}_{}_anonymise".format(
                        self.model._meta.app_label, self.model._meta.model_name
                    )
                ),
                ids=",".join(selected),
            )
        )

    def get_urls(self):
        urls = super(ModelAdmin, self).get_urls()
        extra_urls = [
            re_path(
                r"^anonymise/$",
                self.admin_site.admin_view(self.anonymise_view),
                name="{}_{}_anonymise".format(
                    self.model._meta.app_label, self.model._meta.model_name
                ),
            )
        ]
        return extra_urls + urls

    def anonymise_view(self, request):
        ids_raw = (request.POST or request.GET).get("ids")
        objects = self.model.anonymisable_manager().filter(pk__in=ids_raw.split(","))
        verbose_name = (
            self.model._meta.verbose_name.title()
            if objects.count() == 1
            else self.model._meta.verbose_name_plural.title()
        )
        changelist_url = reverse(
            "admin:{}_{}_changelist".format(
                self.model._meta.app_label, self.model._meta.model_name
            )
        )

        if request.POST:
            objects.anonymise()
            count = objects.count()
            messages.success(request, "{} {} anonymised".format(count, verbose_name))
            return HttpResponseRedirect(changelist_url)

        return TemplateResponse(
            request,
            self.anonymise_template,
            {
                "title": _("Are you sure?"),
                "ids": ids_raw,
                "verbose_name": verbose_name,
                "objects": objects,
                "cancel_url": changelist_url,
            },
        )
