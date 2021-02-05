"""
Test models
"""
from __future__ import unicode_literals

from django.db import models


class ModelWithPrivacyMeta(models.Model):
    """
    Test PrivacyMeta definition on the model
    """

    chars = models.CharField(max_length=255)
    email = models.EmailField()

    class PrivacyMeta:
        fields = ["chars", "email"]
