"""
Test model privacy definitions
"""
try:
    from unittest import mock
except ImportError:
    import mock

from django.apps import apps
from django.db import models
from django.test import TestCase

import gdpr_assist
from gdpr_assist.apps import GdprAppConfig
from gdpr_assist.models import (
    PrivacyManager,
    PrivacyMeta,
    PrivacyModel,
    PrivacyQuerySet,
)
from gdpr_assist.registry import registry

from .base import MigrationTestCase
from .tests_app.models import (
    ModelWithoutPrivacyMeta,
    ModelWithPrivacyMeta,
    ModelWithPrivacyMetaCanNotAnonymise,
    InheritedModelWithPrivacyMeta, InheritedModelWithoutPrivacyMeta,
)


class TestRegistry(TestCase):
    """
    Tests for the registry not covered elsewhere
    """

    def test_register_again__raises_exception(self):
        with self.assertRaises(ValueError) as cm:
            gdpr_assist.register(
                ModelWithPrivacyMeta, ModelWithPrivacyMeta._privacy_meta
            )
        self.assertEqual(
            "Model tests_app.ModelWithPrivacyMeta already registered",
            str(cm.exception),
        )


class TestPrivacyMeta(TestCase):
    """
    Tests for privacy meta not covered elsewhere
    """

    def test_invalid_attribute__raises_attribute_error(self):
        with self.assertRaises(AttributeError) as cm:
            ModelWithPrivacyMeta._privacy_meta.invalid_attr

        self.assertEqual("Attribute invalid_attr not defined", str(cm.exception))


class BaseTestModelDefinition:
    model = None

    def test_model_registered_automatically(self):
        self.assertIn(self.model, registry.models.keys())

    def test_meta_class_removed(self):
        self.assertFalse(hasattr(self.model, "PrivacyMeta"))

    def test_meta_class_instance_added(self):
        self.assertTrue(hasattr(self.model, "_privacy_meta"))
        self.assertIsInstance(self.model._privacy_meta, PrivacyMeta)

    def test_meta_class_instance_registered(self):
        self.assertEqual(
            self.model._privacy_meta, registry.models[self.model]
        )

    def test_privacy_meta_attrs(self):
        meta = self.model._privacy_meta
        self.assertEqual(meta.fields, self.expected_fields)

    def test_model_cast_to_privacy_model(self):
        self.assertTrue(issubclass(self.model, PrivacyModel))

    def test_model_has_anonymised_field(self):
        obj = self.model.objects.create(
            chars="test", email="test@example.com"
        )
        obj.refresh_from_db()
        self.assertFalse(obj.is_anonymised())

    def test_manager_cast_to_privacy_manager(self):
        self.assertIsInstance(self.model.objects, PrivacyManager)

    def test_queryset_cast_to_privacy_queryset(self):
        self.assertIsInstance(self.model.objects.all(), PrivacyQuerySet)

    def test_meta_class_can_anonymise__can(self):
        self.assertTrue(self.model.check_can_anonymise())


class TestModelDefinitionWithPrivacyMeta(BaseTestModelDefinition, TestCase):
    model = ModelWithPrivacyMeta
    expected_fields = ["chars", "email"]

    def test_meta_class_can_anonymise__can_not(self):
        self.assertFalse(ModelWithPrivacyMetaCanNotAnonymise.check_can_anonymise())


class TestModelDefinitionInheritedFromWithPrivacyMeta(BaseTestModelDefinition, TestCase):
    model = InheritedModelWithPrivacyMeta
    expected_fields = ["chars"]


class BaseModelDefinitionWithoutPrivacyMeta:
    model = None

    class PrivacyMeta:
        """
        Test privacy meta class for ModelWithoutPrivacyMeta
        """

        fields = ["chars", "email"]

    def tearDown(self):
        registry.models.pop(self.model, None)
        self.model.__bases__ = tuple(
            b for b in self.model.__bases__ if b is not PrivacyModel
        )

    def register(self):
        gdpr_assist.register(self.model, self.PrivacyMeta)

    def test_model_not_registered(self):
        self.assertNotIn(self.model, registry.models.keys())

    def test_model_registered_manually__is_registered(self):
        self.register()
        self.assertIn(self.model, registry.models.keys())

    def test_model_registered_manually__meta_class_instance_added(self):
        self.register()
        self.assertTrue(hasattr(self.model, "_privacy_meta"))
        self.assertIsInstance(self.model._privacy_meta, PrivacyMeta)

    def test_model_registered_manually__meta_class_instance_registered(self):
        self.register()
        self.assertEqual(
            self.model._privacy_meta,
            registry.models[self.model],
        )

    def test_model_registered_manually__privacy_meta_attrs(self):
        self.register()
        meta = self.model._privacy_meta
        self.assertEqual(meta.fields, self.PrivacyMeta.fields)

    def test_model_registered_manually_without_privacy_meta__meta_class_instance_added(
        self
    ):
        gdpr_assist.register(self.model)
        self.assertTrue(hasattr(self.model, "_privacy_meta"))
        self.assertIsInstance(self.model._privacy_meta, PrivacyMeta)


class TestModelDefinitionWithoutPrivacyMeta(BaseModelDefinitionWithoutPrivacyMeta, TestCase):
    model = ModelWithoutPrivacyMeta


class TestModelDefinitionInheritedWithoutPrivacyMeta(BaseModelDefinitionWithoutPrivacyMeta, TestCase):
    model = InheritedModelWithoutPrivacyMeta


class TestAppConfig(TestCase):
    def setUp(self):
        app_config = apps.get_app_config("gdpr_assist")
        self.app_config = GdprAppConfig(app_config.name, app_config.module)

    @mock.patch("gdpr_assist.registry.registry.models", {})
    @mock.patch("gdpr_assist.registry.registry.watching_on_delete", [])
    def test_register_on_delete_anonymise__finds_target(self):
        TargetMockModel = mock.MagicMock()

        mock_field = mock.MagicMock(spec=models.ForeignKey)
        mock_field.remote_field = mock.MagicMock()
        mock_field.remote_field.on_delete = gdpr_assist.ANONYMISE(None)
        mock_field.related_model = TargetMockModel

        MockModel = mock.MagicMock()
        MockModel._meta.get_fields.return_value = [mock_field]

        registry.models[MockModel] = None

        self.app_config.register_on_delete_anonymise()

        self.assertEqual(registry.watching_on_delete, [TargetMockModel])

    @mock.patch("gdpr_assist.registry.registry.models", {})
    def test_validate_on_delete_anonymise__registered__no_error(self):
        MockModel = mock.MagicMock()
        registry.models[MockModel] = None

        with mock.patch.object(apps, "get_models"):
            apps.get_models.return_value = [MockModel]
            self.app_config.validate_on_delete_anonymise()

    @mock.patch("gdpr_assist.registry.registry.models", {})
    def test_validate_on_delete_anonymise__not_registered__raises_exception(self):
        mock_field = mock.MagicMock(spec=models.ForeignKey)
        mock_field.name = "sample_field"
        mock_field.remote_field = mock.MagicMock()
        mock_field.remote_field.on_delete = gdpr_assist.ANONYMISE(None)

        MockModel = mock.MagicMock()
        MockModel._meta.get_fields.return_value = [mock_field]
        MockModel._meta.app_label = "test"
        MockModel._meta.object_name = "Sample"

        with mock.patch.object(apps, "get_models"):
            apps.get_models.return_value = [MockModel]
            with self.assertRaises(ValueError) as cm:
                self.app_config.validate_on_delete_anonymise()
            self.assertEqual(
                (
                    "Relationship test.Sample.sample_field set to anonymise on "
                    "delete, but model is not registered with gdpr-assist"
                ),
                str(cm.exception),
            )


class TestRegisteredModelMigration(MigrationTestCase):
    """
    Check registered models can be migratated
    """

    def test_manager_deconstruct__deconstructs(self):
        # This should serialise to the privacy manager
        string, imports = self.serialize(ModelWithPrivacyMeta.objects)
        self.assertEqual(string, "gdpr_assist.models.CastPrivacyManager()")

        # And check it serialises back
        obj = self.serialize_round_trip(ModelWithPrivacyMeta.objects)
        self.assertIsInstance(obj, models.Manager)
