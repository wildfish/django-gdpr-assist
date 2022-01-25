"""
Model registry
"""
from . import app_settings


class Registry(object):
    def __init__(self):
        # Register models with privacy meta
        #
        # Data stored as:
        #   {model: privacy_meta, ...}
        self.models = {}

        # Register models we need to monitor for resolving on_delete=ANONYMISE
        # (related models without privacy meta)
        self.watching_on_delete = []

    def register(self, model, privacy_meta=None, gdpr_default_manager_name=None):
        """
        Register this model as one to track
        """
        from .models import PrivacyMeta, PrivacyModel

        if model in self.models:
            raise ValueError(
                "Model {}.{} already registered".format(
                    model._meta.app_label, model._meta.object_name
                )
            )

        # Ensure the PrivacyMeta is a subclass of models.PrivacyMeta
        if privacy_meta is None:
            privacy_meta = PrivacyMeta

        if not issubclass(privacy_meta, PrivacyMeta):
            privacy_meta = type("PrivacyMeta", (privacy_meta, PrivacyMeta, object), {})

        # Instantiate the new class
        privacy_meta = privacy_meta(model, gdpr_default_manager_name)

        # Move the processed PrivacyMeta onto the attribute _privacy_meta
        setattr(model, app_settings.GDPR_PRIVACY_INSTANCE_NAME, privacy_meta)
        if hasattr(model, app_settings.GDPR_PRIVACY_CLASS_NAME):
            delattr(model, app_settings.GDPR_PRIVACY_CLASS_NAME)

        # Register
        self.models[model] = privacy_meta
        PrivacyModel._cast_class(model, privacy_meta)

    def search(self, term):
        """
        Search the registry's models for a given term
        """
        full_results = []
        for model, meta in self.models.items():
            results = meta.search(term)
            if results:
                full_results.append((model, results))
        return full_results

    def models_allowed_to_anonymise(self):
        return [model for model, meta in self.models.items() if meta.can_anonymise]

    def _watch_on_delete(self, model):
        self.watching_on_delete.append(model)

    def __contains__(self, model):
        return model in self.models


registry = Registry()
