from django.test import TestCase

from gdpr_assist.models import EventLog
from gdpr_assist.models import RecursionError

from .gdpr_assist_tests_app.factories import ModelWithPrivacyMetaFactory
from .gdpr_assist_tests_app.models import (
    ForeignKeyFieldModel,
    InvalidFieldModel,
    InvalidFkFieldModel, InvalidSetFieldModel,
    ModelWithPrivacyMeta,
)


class AnonimisationTreeTestCase(TestCase):
    def test_valid_fk_field(self):
        tree = ForeignKeyFieldModel.get_anonymisation_tree()
        self.assertIn("model_with_privacy_meta", tree)
        self.assertIn("ModelWithPrivacyMeta", tree)
        for field in ModelWithPrivacyMeta._privacy_meta.fields:
            self.assertIn(field, tree)
            self.assertIn(field, tree)

    def test_invalid_flat_field(self):
        with self.assertRaises(AttributeError):
            InvalidFieldModel.get_anonymisation_tree()

    def test_invalid_fk_field(self):
        with self.assertRaises(AttributeError):
            InvalidFkFieldModel.get_anonymisation_tree()

    def test_invalid_set_field(self):
        with self.assertRaises(AttributeError):
            InvalidSetFieldModel.get_anonymisation_tree()

    def test_recursion_error(self):
        with self.assertRaises(RecursionError):
            ModelWithPrivacyMeta.get_anonymisation_tree(prefix=11 * "    ")


class EventLogTestCase(TestCase):
    def test_logs_after_anonymise(self):
        instance = ModelWithPrivacyMetaFactory.create()

        self.assertFalse(EventLog.objects.for_instance(instance).exists())
        instance.anonymise()
        self.assertTrue(EventLog.objects.for_instance(instance).exists())

