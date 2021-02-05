"""
Test export functionality
"""
from django.test import TestCase

from model_bakery import baker

from .tests_app.models import (
    FirstSearchModel,
    SecondSearchModel,
    ThirdSearchModel,
)


class TestExport(TestCase):
    def test_export_explicit_fields__fields_correct(self):
        obj = baker.make(FirstSearchModel, chars="test", email="test@example.com")

        data = obj._privacy_meta.export(obj)
        self.assertEqual(data, {"email": "test@example.com"})

    def test_export_implicit_fields__fields_correct(self):
        obj = baker.make(SecondSearchModel, chars="test", email="test@example.com")

        data = obj._privacy_meta.export(obj)
        self.assertEqual(data, {"chars": "test", "email": "test@example.com"})

    def test_export_excluded_fields__fields_correct(self):
        obj = baker.make(ThirdSearchModel, chars="test", email="test@example.com")

        data = obj._privacy_meta.export(obj)
        self.assertEqual(data, {"chars": "test"})
