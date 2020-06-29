from importlib import import_module

from django.apps import apps
from django.db import connection
from django.test import TestCase

from model_mommy import mommy

from .gdpr_assist_tests_app.models import (
    ModelWithPrivacyMeta,
    ModelWithoutPrivacyMeta,
    ModelWithPrivacyMetaAlreadyMigrated,
)

from gdpr_assist.models import PrivacyAnonymised


class TagsTestCase(TestCase):
    def test_0003_migrtion__migrates_data(self):
        already_migrated = mommy.make(ModelWithPrivacyMetaAlreadyMigrated, anonymised=True, _quantity=2)
        mommy.make(ModelWithPrivacyMetaAlreadyMigrated, anonymised=False, _quantity=2)

        data_migration = import_module('gdpr_assist.migrations.0003_migrate_from_v1')
        data_migration.migrate_from_v1(apps, connection.schema_editor())

        self.assertEqual(PrivacyAnonymised.objects.count(), 2)
        self.assertEqual(
            set(PrivacyAnonymised.objects.values_list('object_id', flat=True)),
            {i.pk for i in already_migrated}
        )

    def test_0003_migrtion__no_data_to_migrate(self):
        mommy.make(ModelWithPrivacyMetaAlreadyMigrated, anonymised=False, _quantity=2)

        data_migration = import_module('gdpr_assist.migrations.0003_migrate_from_v1')
        data_migration.migrate_from_v1(apps, connection.schema_editor())

        self.assertEqual(PrivacyAnonymised.objects.count(), 0)

    def test_0003_migrtion__class_without_existing_anonymised_field(self):
        mommy.make(ModelWithPrivacyMeta, _quantity=2)

        data_migration = import_module('gdpr_assist.migrations.0003_migrate_from_v1')
        data_migration.migrate_from_v1(apps, connection.schema_editor())

        self.assertEqual(PrivacyAnonymised.objects.count(), 0)

    def test_0003_migrtion__migrates_data__non_privacy_managed_model(self):
        mommy.make(ModelWithoutPrivacyMeta, _quantity=2)

        data_migration = import_module('gdpr_assist.migrations.0003_migrate_from_v1')
        data_migration.migrate_from_v1(apps, connection.schema_editor())

        self.assertEqual(PrivacyAnonymised.objects.count(), 0)
