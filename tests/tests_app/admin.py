"""
ModelAdmin for testing
"""
from django.contrib import admin
from django.contrib.auth.models import User

import gdpr_assist

from .models import ModelWithPrivacyMeta


class UserPrivacyMeta:
    fields = ["username", "email"]


gdpr_assist.register(User, UserPrivacyMeta, gdpr_default_manager_name="abc")


class PrivacyMetaAdmin(gdpr_assist.admin.ModelAdmin):
    pass


admin.site.unregister(User)
admin.site.register(ModelWithPrivacyMeta, PrivacyMetaAdmin)
admin.site.register(User, PrivacyMetaAdmin)
