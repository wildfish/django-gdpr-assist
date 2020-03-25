from django.db import migrations, models
from django.core.exceptions import FieldDoesNotExist

from gdpr_assist.registry import registry


def migrate_from_v1(apps, schema_editor):
    """
    In V1 data was stored on each model, we need to migrate this to the new link model PrivacyAnonymised
    """
    privacy_model_cls = apps.get_model('gdpr_assist', 'privacyanonymised')
    content_type_cls = apps.get_model('contenttypes', 'ContentType')

    to_create = []

    for model in registry.models.keys():
        try:
            model_cls = apps.get_model(model._meta.app_label, model._meta.model_name)
            # we must via the apps model, i.e. not the registry version.
            model_cls._meta.get_field('anonymised')
            # same with content type
            ct = content_type_cls.objects.get_for_model(model_cls)

            for obj in model_cls.objects.filter(anonymised=True):
                to_create.append(privacy_model_cls(object_id=obj.id, content_type=ct))
        except FieldDoesNotExist:
            # linked to privacy but never migrated/or this is the first run.
            pass

    privacy_model_cls.objects.bulk_create(to_create)


def downgrade_from_v1(apps, schema_editor):
    """
        No action to take on downgrade in terms of data.
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('gdpr_assist', '0002_privacyanonymised'),
    ]

    operations = [
        migrations.RunPython(migrate_from_v1, downgrade_from_v1, hints={'model_name': 'privacyanonymised'}),
    ]
