"""
gdpr-assist app definition
"""
from django.apps import AppConfig, apps
from django.db import models

from . import upgrading  # noqa
from .deletion import ANONYMISE
from .registry import registry


def is_on_delete_anonymise(field):
    if not isinstance(field, (models.OneToOneField, models.ForeignKey)):
        return False

    if hasattr(field, "remote_field"):
        remote_field = field.remote_field
    elif hasattr(field, "rel"):
        remote_field = field.rel
    else:  # pragma: no cover
        raise ValueError("Unexpected remote field attribute")
    return isinstance(remote_field.on_delete, ANONYMISE)


class GdprAppConfig(AppConfig):
    name = "gdpr_assist"
    verbose_name = "GDPR"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        """
        When all models are loaded, look at all registered privacy models and
        see if there are any related models we also need to be interested in.
        """
        self.register_on_delete_anonymise()
        self.validate_on_delete_anonymise()

    def register_on_delete_anonymise(self):
        """
        Look for ANONYMISE relations from models we're watching, and register
        them with registry.watching_on_delete
        """
        for model in registry.models.keys():
            relation_fields = [
                field
                for field in model._meta.get_fields()
                if is_on_delete_anonymise(field)
            ]

            for field in relation_fields:
                if (
                    field.related_model not in registry
                    and field.related_model not in registry.watching_on_delete
                ):
                    registry._watch_on_delete(field.related_model)

    def validate_on_delete_anonymise(self):
        """
        Look for invalid ANONYMISE relations on other models
        """
        for model in apps.get_models():
            # on_delete=ANONYMISE is ok on models registered with privacy
            if model in registry.models:
                continue

            # But not any other models
            for field in model._meta.get_fields():
                if is_on_delete_anonymise(field):
                    raise ValueError(
                        (
                            "Relationship {}.{}.{} set to anonymise on delete,"
                            " but model is not registered with gdpr-assist"
                        ).format(
                            model._meta.app_label, model._meta.object_name, field.name
                        )
                    )
