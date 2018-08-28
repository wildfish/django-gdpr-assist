"""
Signal handlers
"""
from django.db.models.signals import class_prepared, pre_delete, post_delete
from django.dispatch import receiver

from . import app_settings
from .anonymiser import anonymise_related_objects
from .registry import registry


@receiver(class_prepared)
def register_model(sender, **kwargs):
    """
    Register any models with a privacy meta class
    """
    Privacy = sender.__dict__.get(app_settings.GDPR_PRIVACY_CLASS_NAME)
    if Privacy:
        registry.register(sender, Privacy)


@receiver(pre_delete)
def handle_pre_delete(sender, instance, using, **kwargs):
    if sender in registry or sender in registry.watching_on_delete:
        return anonymise_related_objects(instance)


@receiver(post_delete)
def handle_post_delete(sender, instance, using, **kwargs):
    if sender in registry:
        instance._log_gdpr_delete()
