"""
ModelAdmin for testing
"""
from django.contrib import admin

import gdpr_assist

from .models import ModelWithPrivacyMeta


class ModelWithPrivacyMetaAdmin(gdpr_assist.admin.ModelAdmin):
    pass


admin.site.register(ModelWithPrivacyMeta, ModelWithPrivacyMetaAdmin)
