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


``GDPR_LOG_ON_ANONYMISE = True``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Set this to ``False`` to disable entries being created on the fly in the logging
database (see ``GDPR_LOG_DATABASE_NAME``) during anonymisation, this may be useful
for large initial anonyimisation tasks.

By default log entries are created when a instance is anonymised and in bulk when
calling the ``anonymise_db`` command.

If you set this to ``False`` you can manually create logging for any instance you
have anonymised later via ``instance._log_gdpr_anonymise()``, handling
``post_anonymise`` signal or processing over ``PrivacyAnonymised`` as required i.e
a celery queue or cronjob.


``SILENCED_SYSTEM_CHECKS``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default, gdpr-assist performs migration checks to ensure that you've followed
the upgrade instructions correctly to avoid accidental data loss.

See :doc:`upgrading` for more details of the specific checks.

They may cause a slight performance hit to management command which run checks, so while
we recommend you leave them on while upgrading, once the upgrade has been completed and
succesfully deployed the checks can safely be disabled afterwards by adding them to
Django's `SILENCED_SYSTEMS_CHECKS`__ setting::

    SILENCED_SYSTEM_CHECKS = [
        "gdpr_assist.E001",
    ]

__ https://docs.djangoproject.com/en/3.0/ref/settings/#silenced-system-checks
