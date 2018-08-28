============
Installation
============

Install with::

    pip install django-gdpr-assist


Add to your project's ``settings.py``::

    # Add the app
    INSTALLED_APPS = (
        ...
        'gdpr_assist',
        ...
    )

    # Add a new database to log GDPR actions
    DATABASES = {
        ...
        'gdpr_log': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'gdpr-log.sqlite3'),
        },
    }
    DATABASE_ROUTERS = ['gdpr_assist.routers.EventLogRouter']

You'll then need to migrate the new database::

    ./manage.py migrate --database=gdpr_log


Django settings
===============

In addition to the required changes to your settings  listed above, there are
additional optional settings which you can define to override default
behaviour:


``GDPR_PRIVACY_CLASS_NAME = 'PrivacyMeta'``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This allows you to override the default name of the privacy meta class on
models.


``GDPR_PRIVACY_INSTANCE_NAME = '_privacy_meta'``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This allows you to override the default name of the instantiated privacy meta
class on models.


``GDPR_LOG_DATABASE_NAME = 'gdpr_log'``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The internal name of the log database. You'll need to use this in the
``DATABASES`` settings, and when migrating.


``GDPR_CAN_ANONYMISE_DATABASE = False``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Set this to ``True`` to enable the ``anonymise_db`` management command. You
will want this to be ``False`` on your production deployment.

