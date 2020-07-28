from django.test import TestCase

import gdpr_assist
from .gdpr_assist_tests_app.models import (
    ForeignKeyFieldModel,
    ModelWithPrivacyMeta,
)


class AnonimisationTreeTestCase(TestCase):
    def test_valid_fk_Field(self):
        tree = ForeignKeyFieldModel.get_anonymisation_tree()
        self.assertIn("model_with_privacy_meta", tree)
        self.assertIn("ModelWithPrivacyMeta", tree)
        for field in ModelWithPrivacyMeta._privacy_meta.fields:
            self.assertIn(field, tree)
            self.assertIn(field, tree)

    def test_invalid_flat_Field(self):
        class BogusModel(ModelWithPrivacyMeta):
            class PrivacyMeta:
                fields = ["inexisting_field"]

        with self.assertRaises(AttributeError):
            BogusModel.get_anonymisation_tree()

    def test_invalid_fk_Field(self):

        class BogusModel(ModelWithPrivacyMeta):
            class PrivacyMeta:
                fk_fields = ["inexisting_field"]

        with self.assertRaises(AttributeError):
            BogusModel.get_anonymisation_tree()

    def test_invalid_set_Field(self):

        class BogusModel(ModelWithPrivacyMeta):
            class PrivacyMeta:
                set_fields = ["inexisting_field"]

        with self.assertRaises(AttributeError):
            BogusModel.get_anonymisation_tree()
