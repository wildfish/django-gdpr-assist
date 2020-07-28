"""
Test export functionality
"""
from django.test import TestCase

from .gdpr_assist_tests_app.factories import (
    FirstSearchModelFactory,
    SecondSearchModelFactory,
    ThirdSearchModelFactory,
)


class TestExport(TestCase):
    def test_export_explicit_fields__fields_correct(self):
        obj = FirstSearchModelFactory.create(
            chars='test',
            email='test@example.com',
        )

        data = obj._privacy_meta.export(obj)
        self.assertEqual(
            data,
            {'email': 'test@example.com'},
        )

    def test_export_implicit_fields__fields_correct(self):
        obj = SecondSearchModelFactory.create(
            chars='test',
            email='test@example.com',
        )

        data = obj._privacy_meta.export(obj)
        self.assertEqual(
            data,
            {
                'chars': 'test',
                'email': 'test@example.com',
            },
        )

    def test_export_excluded_fields__fields_correct(self):
        obj = ThirdSearchModelFactory.create(
            chars='test',
            email='test@example.com',
        )

        data = obj._privacy_meta.export(obj)
        self.assertEqual(
            data,
            {
                'chars': 'test',
            },
        )
