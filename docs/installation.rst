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


``GDPR_CAN_ANONYMISE_DATABASE = False``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Set this to ``True`` to enable the ``anonymise_db`` management command. You
will want this to be ``False`` on your production deployment.

