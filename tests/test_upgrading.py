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

    # Test apps we're working work
    test_apps = {
        "anonymised_migration",
        "missing_anonymised_migration",
        "no_anonymised_migration",
    }

    # Migrate back to this
    migrate_from = None

    # Migrate forward to this (optional)
    migrate_to = None

    @classmethod
    def setUpClass(cls):
        # Capture current state before adding any apps, so we know where to restore to
        executor = MigrationExecutor(connections[DEFAULT_DB_ALIAS])
        cls._original_state = executor.loader.graph.leaf_nodes()

        super().setUpClass()

    def setUp(self):
        # Keep track of any test apps we migrate
        self.test_apps_migrated = set()

        # Migrate back
        self._migrate(self.migrate_from)

        self.setUpData()

        # Migrate forward
        if self.migrate_to is not None:
            self._migrate(self.migrate_to)

        super().setUp()

    def tearDown(self):
        # Migrate back
        if self.migrate_to is not None:
            self._migrate(self.migrate_from)

        # Make sure we've migrated out the test apps we've spotted
        if self.test_apps_migrated:
            self._migrate([(test_app, None) for test_app in self.test_apps_migrated])

        # Restore back to the original
        # The MigrationLoader will check the active django.apps.apps, so we need to
        # create a modified migration plan to exclude our test apps
        executor = MigrationExecutor(connections[DEFAULT_DB_ALIAS])
        executor.loader.build_graph()
        plan = executor.migration_plan(self._original_state)
        filtered_plan = [
            pair for pair in plan if pair[0].app_label not in self.test_apps
        ]
        executor.migrate(self._original_state, plan=filtered_plan)

        super().tearDown()

    def setUpData(self):
        """
        Opportunity for subclasses to add data

        Run after migrate_from, before migrate_to
        """

    def _migrate(self, target):
        executor = MigrationExecutor(connections[DEFAULT_DB_ALIAS])
        executor.loader.build_graph()

        # See if the migration plan includes any of our test apps, so we know which to
        # clean up in the tearDown
        plan_apps = [
            pair[0] for pair in self.plan_to_names(executor.migration_plan(target))
        ]
        test_apps = self.test_apps.intersection(set(plan_apps))
        self.test_apps_migrated.update(test_apps)

        # Perform the actual migration and refresh the graph
        executor.migrate(target)
        executor.loader.build_graph()

    def plan_to_names(self, plan):
        """
        Convert migration plan to something we can compare easily
        """
        return [(pair[0].app_label, pair[0].name) for pair in plan]


class TestMigrateGdprAnonymisedCheck(MigrationTestCase):
    """
    Assume we're migrating everything at once
    """

    # Roll back migrations to gdpr_assist.0001_initial
    migrate_from = [("gdpr_assist", "0001_initial")]

    @modify_settings(
        INSTALLED_APPS={
            "append": "tests.test_migrations.anonymised_migration"
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
                ('gdpr_assist', '0003_auto_20210205_1657'),
                ('gdpr_assist', '0004_auto_20211215_1057')
            ],
        )

        # Run check
        errors = check_migrate_gdpr_anonymised(executor.loader.project_state().apps)
        self.assertEqual(len(errors), 0)

    @modify_settings(
        INSTALLED_APPS={
            "append": "tests.test_migrations.no_anonymised_migration"
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
                ('gdpr_assist', '0003_auto_20210205_1657'),
                ('gdpr_assist', '0004_auto_20211215_1057'),
                ("no_anonymised_migration", "0002_auto_20201020_0102"),
            ],
        )

        # Run check
        errors = check_migrate_gdpr_anonymised(executor.loader.project_state().apps)
        self.assertEqual(len(errors), 0)

    @modify_settings(
        INSTALLED_APPS={
            "append": "tests.test_migrations.missing_anonymised_migration"
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
                ('gdpr_assist', '0003_auto_20210205_1657'),
                ('gdpr_assist', '0004_auto_20211215_1057'),
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
    INSTALLED_APPS={"append": "tests.test_migrations.anonymised_migration"}
)
class TestMGASeparateMigratesAnonymisedCheck(MigrationTestCase):
    """
    Assume we're migrating gdpr-assist, then creating migrations, then migrating our
    models
    """

    # Simulate migration gdpr-assist first
    migrate_from = [("gdpr_assist", "0001_initial")]
    migrate_to = [("gdpr_assist", "0002_privacyanonymised")]

    def test_anonymised_migration_uses_operator__check_passes(self):
        executor = MigrationExecutor(connections[DEFAULT_DB_ALIAS])
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())

        # Sanity check - confirm plan is what we expected from Django
        self.assertEqual(
            self.plan_to_names(plan),
            [
                ('anonymised_migration', '0002_migrate_anonymised'),
                ('anonymised_migration', '0003_auto_20201020_0102'),
                ('gdpr_assist', '0003_auto_20210205_1657'),
                ('gdpr_assist', '0004_auto_20211215_1057'),
            ],
        )

        # Run check
        errors = check_migrate_gdpr_anonymised(executor.loader.project_state().apps)
        self.assertEqual(len(errors), 0)


@modify_settings(
    INSTALLED_APPS={
        "append": "tests.test_migrations.missing_anonymised_migration"
    }
)
class TestMGASeparateMigratesMissingAnonymisedCheck(MigrationTestCase):
    """
    Assume we're migrating gdpr-assist, then creating migrations, then migrating our
    models
    """

    # Simulate migration gdpr-assist first
    migrate_from = [("gdpr_assist", "0001_initial")]
    migrate_to = [("gdpr_assist", "0002_privacyanonymised")]

    def test_missing_anonymised_migration__check_fails(self):
        executor = MigrationExecutor(connections[DEFAULT_DB_ALIAS])
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())

        # Sanity check - confirm plan is what we expected from Django
        self.assertEqual(
            self.plan_to_names(plan),
            [
                ('gdpr_assist', '0003_auto_20210205_1657'),
                ('gdpr_assist', '0004_auto_20211215_1057'),
                ("missing_anonymised_migration", "0002_auto_20201020_0102")
            ]
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
    INSTALLED_APPS={"append": "tests.test_migrations.anonymised_migration"}
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
    INSTALLED_APPS={"append": "tests.test_migrations.anonymised_migration"}
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
