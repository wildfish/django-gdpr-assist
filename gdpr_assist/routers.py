"""
Database router for event logging
"""
from . import app_settings


class EventLogRouter:
    privacy_model = "privacyanonymised"

    def _route_model(self, model):
        """
        Route to log table for all gdpr actions.

        Except for the PrivacyAnonymised, which needs to be in main db.
        """
        if (
            model._meta.app_label == "gdpr_assist"
            and model._meta.model_name != self.privacy_model
        ):
            return app_settings.GDPR_LOG_DATABASE_NAME
        return None

    def db_for_read(self, model, **hints):
        return self._route_model(model)

    def db_for_write(self, model, **hints):
        return self._route_model(model)

    def allow_relation(self, obj1, obj2, **hints):
        return obj1._state.db == obj2._state.db

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Only allow gdpr_assist models in the GDPR_LOG database, and keep them
        out of the main database.

        Except for the PrivacyAnonymised, which needs to be in main db.
        """
        if db == app_settings.GDPR_LOG_DATABASE_NAME:
            if app_label == "gdpr_assist" and model_name != self.privacy_model:
                return True
            else:
                return False
        elif app_label == "gdpr_assist":
            return self.privacy_model == model_name
        return None
