"""
Tools to assist with upgrades
"""
from collections import defaultdict

from django.conf import settings
from django.core.checks import Error, Tags, register
from django.core.exceptions import ImproperlyConfigured
from django.db import DEFAULT_DB_ALIAS, connections, migrations, router
from django.db.migrations.exceptions import MigrationSchemaMissing
from django.db.migrations.operations.base import Operation


class MigrateGdprAnonymised(Operation):
    # Based on RunPython

    def __init__(self, model_name):
        self.model_name = model_name

    def deconstruct(self):
        kwargs = {"model_name": self.model_name}
        return (self.__class__.__name__, [], kwargs)

    def state_forwards(self, app_label, state):
        pass

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        # Checks from RunPython
        from_state.clear_delayed_apps_cache()
        if not router.allow_migrate(schema_editor.connection.alias, app_label):
            return

        # Look up models
        apps = from_state.apps
        privacy_model_cls = apps.get_model("gdpr_assist", "privacyanonymised")
        content_type_cls = apps.get_model("contenttypes", "ContentType")
        model_cls = apps.get_model(app_label, self.model_name)

        # Get content type frot his model
        ct = content_type_cls.objects.get_for_model(model_cls)

        # Find all anonymised objects
        to_create = []
        for obj in model_cls.objects.filter(anonymised=True):
            to_create.append(privacy_model_cls(object_id=obj.id, content_type=ct))

        # Add them to PrivacyAnonymised
        privacy_model_cls.objects.bulk_create(to_create)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        # Checks from RunPython
        if not router.allow_migrate(schema_editor.connection.alias, app_label):
            return

        # Look up models
        apps = from_state.apps
        privacy_model_cls = apps.get_model("gdpr_assist", "privacyanonymised")
        content_type_cls = apps.get_model("contenttypes", "ContentType")
        model_cls = apps.get_model(app_label, self.model_name)

        # Find all anonymised objects
        ct = content_type_cls.objects.get_for_model(model_cls)
        object_ids = privacy_model_cls.objects.filter(content_type=ct).values_list(
            "object_id", flat=True
        )

        # the GFK may not be of the same type, so ensure the values is prepped correctly for model_cls.
        object_ids = [model_cls._meta.pk.get_prep_value(o) for o in object_ids]

        # Set the anonymised field
        model_cls.objects.filter(pk__in=object_ids).update(anonymised=True)

    def describe(self):
        return "Migrate a model managed by gdpr-assist from v1.1.0"


@register(Tags.models)
def check_migrate_gdpr_anonymised(app_configs, **kwargs):
    """
    Check that the developers using gdpr-assist have read the instructions for upgrading
    from version 1.1.0
    """
    # Check is optional
    # Normally SILENCED_SYSTEM_CHECKS would let the check run, and errors couldn't be
    # silenced. We'll abuse the setting in the interest of keeping configuration simple.
    if "gdpr_assist.E001" in settings.SILENCED_SYSTEM_CHECKS:
        return []

    # Import here instead of top level as django.apps won't be available at import time
    from django.db.migrations.executor import MigrationExecutor

    errors = []

    try:
        executor = MigrationExecutor(connections[DEFAULT_DB_ALIAS])
    except ImproperlyConfigured:
        # No databases are configured (or the dummy one)
        return
    except MigrationSchemaMissing:
        # No migration table, migrations will already warn about this
        return

    # Step through migration plan looking for relevant migrations
    migrated_models = defaultdict(dict)
    plan = executor.migration_plan(executor.loader.graph.leaf_nodes(), clean_start=True)
    for migration, is_backwards in plan:
        # Don't worry about reverse migrations
        if is_backwards:
            continue

        # Look at operations
        for op in migration.operations:
            app_label = migration.app_label.lower()
            model_name = getattr(op, "model_name", "").lower()

            # When we see a migrated field, we can ignore it in future migrations
            if isinstance(op, MigrateGdprAnonymised):
                migrated_models[app_label][model_name] = True

            # When we see an "anonymised" field being removed without it first being
            # migrated or the migration being explicitly marked as safe, raise an error
            elif (
                not getattr(migration, "gdpr_assist_safe", False)
                and isinstance(op, migrations.RemoveField)
                and op.name == "anonymised"
                and model_name not in migrated_models[app_label]
            ):
                errors.append(
                    Error(
                        "Removing anonymised field before its data is migrated",
                        hint="See https://django-gdpr-assist.readthedocs.io/en/latest/upgrading.html for upgrade instructions from v1.1.0",
                        id="gdpr_assist.E001",
                    )
                )

    return errors
