"""
Test model privacy definitions
"""
from django.contrib.contenttypes.models import ContentType
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.state import ProjectState, ModelState

try:
    from unittest import mock
except ImportError:
    import mock

from django.apps import apps
from django.contrib.auth.models import User, UserManager, Group, Permission
from django.db import models, connection
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

from .base import SimpleMigrationTestCase
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
        manager = self.model.objects
        self.assertIsInstance(manager, PrivacyManager)
        self.assertEqual(
            f"{manager.__module__}.{manager.__class__.__name__}",
            "django.db.models.manager.CastPrivacyManager"
        )

        alt_manager = self.model.anonymisable_manager()
        self.assertIsInstance(alt_manager, PrivacyManager)
        self.assertEqual(
            f"{alt_manager.__module__}.{alt_manager.__class__.__name__}",
            "django.db.models.manager.CastPrivacyManager"
        )

    def test_queryset_cast_to_privacy_queryset(self):
        qs = self.model.objects.all()
        self.assertIsInstance(qs, PrivacyQuerySet)
        self.assertEqual(
            f"{qs.__module__}.{qs.__class__.__name__}",
            "django.db.models.query.CastPrivacyQuerySet"
        )

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
        self.model.objects = models.Manager()

    def register(self, gdpr_default_manager_name=None):
        gdpr_assist.register(self.model, self.PrivacyMeta, gdpr_default_manager_name)

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

    def test_model_registered_manually_manager_cast_name_is_default(self):
        self.register()
        self.assertIsInstance(self.model.objects, PrivacyManager)

    def test_model_registered_manually_manager_cast_name_is_as_specified(self):
        self.register(gdpr_default_manager_name="abc")
        self.assertNotIsInstance(self.model.objects, PrivacyManager)
        self.assertIsInstance(self.model.abc, PrivacyManager)


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


class TestRegisteredModelMigration(SimpleMigrationTestCase):
    """
    Check registered models can be migrated
    """

    def test_manager_deconstruct__deconstructs(self):
        # This should serialise to the privacy manager
        string, imports = self.serialize(ModelWithPrivacyMeta.objects)
        self.assertEqual(string, "django.db.models.manager.CastPrivacyManager()")

        # And check it serialises back
        obj = self.serialize_round_trip(ModelWithPrivacyMeta.objects)
        self.assertIsInstance(obj, models.Manager)


class TestExternalUseInMigration(TestCase):
    """
    Tests to ensure that no migrations are created for any registered models.
    """
    def _add_user_project_state_models(self, project_state):
        """ To test ProjectState() on User we will always need to add related."""
        for model in [User, Group, Permission, ContentType]:
            project_state.add_model(ModelState.from_model(model))

    def _register(self, default_manager_name):
        class UserPrivacyMeta:
            fields = ["username", "email"]

        gdpr_assist.register(User, UserPrivacyMeta, default_manager_name)

    def _deregister(self):
        registry.models.pop(User, None)
        User.__bases__ = tuple(
            b for b in User.__bases__ if b is not PrivacyModel
        )

    def setUp(self):
        self._deregister()
        self._register("abc")

    def test_registering_external_does_not_change_state(self):
        project_state_before_register = ProjectState()
        self._add_user_project_state_models(project_state_before_register)

        # Ensure User manager is use_in_migrations
        self.assertTrue(User.objects.use_in_migrations)

        project_state_after_register = ProjectState()
        self._add_user_project_state_models(project_state_after_register)

        executor = MigrationExecutor(connection)
        autodetector = MigrationAutodetector(
            project_state_before_register, project_state_after_register
        )

        changes = autodetector.changes(graph=executor.loader.graph)
        self.assertEqual({}, changes)

    def test_manager_original_objects_not_cast(self):
        # registered in test_app/admin.py
        self.assertIsInstance(User.objects, UserManager)
        self.assertIsInstance(User.abc, PrivacyManager)
        self.assertIsInstance(User.anonymisable_manager(), PrivacyManager)


    def test_manager_gdpr_default_manager_name_not_set(self):
        self._deregister()

        class UserPrivacyMeta:
            fields = ["username", "email"]

        with self.assertRaises(RuntimeError) as ex:
            gdpr_assist.register(User, UserPrivacyMeta)


        self.assertEqual(
            str(ex.exception),
            "Registered gdpr_assist model Users manager specified 'use_in_migrations=True', with no name provided."
        )
        self.assertIsInstance(User.objects, UserManager)
        self.assertNotIsInstance(User.objects, PrivacyManager)
