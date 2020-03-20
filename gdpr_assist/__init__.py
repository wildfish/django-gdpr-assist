"""
Module-level definitions for convenient access
"""
from .deletion import ANONYMISE  # noqa
from .exceptions import AnonymiseError  # noqa


__version__ = '1.1.0'

default_app_config = 'gdpr_assist.apps.GdprAppConfig'


def register(model, privacy_meta=None):
    from .registry import registry
    registry.register(model, privacy_meta)
