from django.db import DEFAULT_DB_ALIAS, connections
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, modify_settings

from model_bakery import baker

from gdpr_assist.models import PrivacyAnonymised
from gdpr_assist.upgrading import check_migrate_gdpr_anonymised


class MigrationTestCase(TransactionTestCase):
    """
    Base class for migration-related tests
    """

    # Migrate back to this
    migrate_from = None

    # Migrate forward to this (optional)
    migrate_to = None

    def setUp(self):
        # Have to do it in the class model before we enter the transaction

        # Capture current state
        self.executor = MigrationExecutor(connections[DEFAULT_DB_ALIAS])
        self._original_state = self.executor.loader.graph.leaf_nodes()

        # Migrate back
        self._migrate(self.migrate_from)

        self.setUpData()

        # Migrate forward
        if self.migrate_to is not None:
            self._migrate(self.migrate_to)

        super().setUp()

    def tearDown(self):
        super().tearDown()

        # Migrate back
        if self.migrate_to is not None:
            self._migrate(self.migrate_from)

        self.tearDownData()

        # Restore
        self._migrate(self._original_state)

    def setUpData(self):
        """
        Opportunity for subclasses to add data

        Run after migrate_from, before migrate_to
        """

    def tearDownData(self):
        """
        Subclasses need to tidy up their data themselves as we're outside transactions

        Run in the state of migrate_from - after reversing migrate_to, before restoring
        state
        """

    def _migrate(self, target):
        self.executor = MigrationExecutor(connections[DEFAULT_DB_ALIAS])
        self.executor.migrate(target)

    def plan_to_names(self, plan):
        """
        Convert migration plan to something we can compare easily
        """
        return [(pair[0].app_label, pair[0].name) for pair in plan]


class TestMigrateGdprAnonymisedCheck(MigrationTestCase):
    # Roll back migrations to gdpr_assist.0001_initial
    migrate_from = [("gdpr_assist", "0001_initial")]

    @modify_settings(
        INSTALLED_APPS={
            "append": "tests.gdpr_assist_test_migrations.anonymised_migration"
        }
    )
    def test_anonymised_migration_uses_operator__check_passes(self):

        executor = MigrationExecutor(connections[DEFAULT_DB_ALIAS])
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())

        # Sanity check - confirm plan is what we expected from Django
        self.assertEqual(
            self.plan_to_names(plan),
            [
                ("anonymised_migration", "0001_initial"),
                ("gdpr_assist", "0002_privacyanonymised"),
                ("anonymised_migration", "0002_migrate_anonymised"),
                ("anonymised_migration", "0003_auto_20201020_0102"),
            ],
        )

        # Run check
        errors = check_migrate_gdpr_anonymised(executor.loader.project_state().apps)
        self.assertEqual(len(errors), 0)

    @modify_settings(
        INSTALLED_APPS={
            "append": "tests.gdpr_assist_test_migrations.no_anonymised_migration"
        }
    )
    def test_no_anonymised_migration_uses_flag__check_passes(self):

        executor = MigrationExecutor(connections[DEFAULT_DB_ALIAS])
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())

        # Sanity check - confirm plan is what we expected from Django
        self.assertEqual(
            self.plan_to_names(plan),
            [
                ("no_anonymised_migration", "0001_initial"),
                ("gdpr_assist", "0002_privacyanonymised"),
                ("no_anonymised_migration", "0002_auto_20201020_0102"),
            ],
        )

        # Run check
        errors = check_migrate_gdpr_anonymised(executor.loader.project_state().apps)
        self.assertEqual(len(errors), 0)

    @modify_settings(
        INSTALLED_APPS={
            "append": "tests.gdpr_assist_test_migrations.missing_anonymised_migration"
        }
    )
    def test_missing_anonymised_migration__check_fails(self):
        executor = MigrationExecutor(connections[DEFAULT_DB_ALIAS])
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())

        # Sanity check - confirm plan is what we expected from Django
        self.assertEqual(
            self.plan_to_names(plan),
            [
                ("missing_anonymised_migration", "0001_initial"),
                ("gdpr_assist", "0002_privacyanonymised"),
                ("missing_anonymised_migration", "0002_auto_20201020_0102"),
            ],
        )

        # Run check
        errors = check_migrate_gdpr_anonymised(executor.loader.project_state().apps)
        self.assertEqual(len(errors), 1)
        error = errors[0]
        self.assertEqual(
            error.msg, "Removing anonymised field before its data is migrated"
        )
        self.assertEqual(error.id, "gdpr_assist.E001")


@modify_settings(
    INSTALLED_APPS={"append": "tests.gdpr_assist_test_migrations.anonymised_migration"}
)
class TestMigrateGdprAnonymisedOperator(MigrationTestCase):
    migrate_from = [("anonymised_migration", "0001_initial")]
    migrate_to = [("anonymised_migration", "0002_migrate_anonymised")]

    def setUpData(self):

        executor = MigrationExecutor(connections[DEFAULT_DB_ALIAS])
        apps = executor.loader.project_state(self.migrate_from).apps
        ModelWithPrivacyMeta = apps.get_model(
            "anonymised_migration", "ModelWithPrivacyMeta"
        )

        self.obj1 = baker.make(ModelWithPrivacyMeta, anonymised=False)
        self.obj2 = baker.make(ModelWithPrivacyMeta, anonymised=True)

    def test_operator__anonymised_copied(self):
        anon1 = PrivacyAnonymised.objects.filter(object_id=self.obj1.pk).count()
        anon2 = PrivacyAnonymised.objects.filter(object_id=self.obj2.pk).count()
        self.assertEqual(anon1, 0)
        self.assertEqual(anon2, 1)


@modify_settings(
    INSTALLED_APPS={"append": "tests.gdpr_assist_test_migrations.anonymised_migration"}
)
class TestMigrateGdprAnonymisedReverseOperator(MigrationTestCase):
    migrate_from = [("anonymised_migration", "0002_migrate_anonymised")]
    migrate_to = [("anonymised_migration", "0001_initial")]

    def setUpData(self):

        executor = MigrationExecutor(connections[DEFAULT_DB_ALIAS])
        apps = executor.loader.project_state(self.migrate_from).apps
        privacy_model_cls = apps.get_model("gdpr_assist", "privacyanonymised")
        ModelWithPrivacyMeta = apps.get_model(
            "anonymised_migration", "ModelWithPrivacyMeta"
        )

        content_type_cls = apps.get_model("contenttypes", "ContentType")
        ct = content_type_cls.objects.get_for_model(ModelWithPrivacyMeta)

        self.obj1 = baker.make(ModelWithPrivacyMeta)
        self.obj2 = baker.make(ModelWithPrivacyMeta)
        privacy_model_cls.objects.create(content_type=ct, object_id=self.obj2.pk)

    def test_operator__anonymised_copied(self):
        self.obj1.refresh_from_db()
        self.obj2.refresh_from_db()
        self.assertEqual(self.obj1.anonymised, False)
        self.assertEqual(self.obj2.anonymised, True)
