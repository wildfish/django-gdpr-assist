"""
Database router for event logging
"""
from . import app_settings


class EventLogRouter:
    def _route_model(self, model):
        if model._meta.app_label == 'gdpr_assist':
            return app_settings.GDPR_LOG_DATABASE_NAME
        return None

    def db_for_read(self, model, **hints):
        return self._route_model(model)

    def db_for_write(self, model, **hints):
        return self._route_model(model)

    def allow_relation(self, obj1, obj2, **hints):
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Only allow gdpr_assist models in the GDPR_LOG database, and keep them
        out of the main database.
        """
        if db == app_settings.GDPR_LOG_DATABASE_NAME:
            if app_label == 'gdpr_assist':
                return True
            else:
                return False
        elif app_label == 'gdpr_assist':
            return False
        return None
