"""
Settings
"""
from yaa_settings import AppSettings


class PrivacySettings(AppSettings):
    # Name of the model attribute for a privacy definition
    GDPR_PRIVACY_CLASS_NAME = 'PrivacyMeta'

    # Name of the model attribute for the privacy definition instance
    GDPR_PRIVACY_INSTANCE_NAME = '_privacy_meta'

    # Internal name for the GDPR log database
    GDPR_LOG_DATABASE_NAME = 'gdpr_log'

    # Disable anonymise_db command by default - we don't want people running it
    # on production by accident
    GDPR_CAN_ANONYMISE_DATABASE = False
