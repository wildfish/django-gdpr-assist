"""
Test models
"""
from __future__ import unicode_literals

from django.db import models


class ModelWithoutPrivacyMeta(models.Model):
    """
    Model without PrivacyMeta which has an ``anonymised`` field
    """

    chars = models.CharField(max_length=255)
    anonymised = models.BooleanField(default=False)
    email = models.EmailField()
