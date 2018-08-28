============
Contributing
============

Contributions are welcome by pull request. Check the github issues and project
:ref:`roadmap <roadmap>` to see what needs work.


Installing
==========

The easiest way to work on GDPR-assist is to fork the project on github, then
install it to a virtualenv::

    virtualenv django-gdpr-assist
    cd django-gdpr-assist
    source bin/activate
    pip install -e git+git@github.com:USERNAME/django-gdpr-assist.git#egg=django-gdpr-assist[dev]

(replacing ``USERNAME`` with your username).

This will install the development dependencies too, and you'll find the
source ready for you to work on in the ``src`` folder of your virtualenv.


Testing
=======

Contributions will be merged more quickly if they are provided with unit tests.

Use ``setup.py`` to run the python tests on your current python environment;
you can optionally specify which test to run::

    python setup.py test [tests[.test_set.TestClass]]

Use ``tox`` to run them on one or more supported versions::

    tox [-e py36-django1.11] [tests[.test_module.TestClass]]

Tox will also generate a ``coverage`` HTML report.

You can also use ``detox`` to run the tests concurrently, although you will
need to run ``tox -e report`` again afterwards to generate the coverage report.

To use a different database (mysql, postgres etc) use the environment variables
``DATABASE_ENGINE``, ``DATABASE_NAME``, ``DATABASE_USER``,
``DATABASE_PASSWORD``,  ``DATABASE_HOST`` and ``DATABASE_PORT``, eg::

    DATABASE_ENGINE=pgsql DATABASE_NAME=gdpr_assist_test [...] tox


Code overview
=============

The ``handlers.register_model`` handler watches for new model definitions which
include a ``PrivacyMeta`` attribute. These models are then registered
automatically with the ``registry.registry``.

Registration casts and instantiates the ``PrivacyMeta`` and stores it on the
``_privacy_meta`` attribute of the model. It also changes the base class of the
model to ``models.PrivacyModel``, its manager to ``models.PrivacyManager``
and its queryset to ``models.PrivacyQuerySet`` to add the necessary
anonymisation attributes and methods.

Once all models are registered, ``apps.GdprAppConfig.ready`` looks at all
registered models for a ``OneToOneField`` or ``ForeignKey`` which have
``on_delete=ANONYMISE(..)``, and then logs the related models with the registry
so that ``handlers.handle_pre_delete`` knows to watch them.

When a registered object is deleted, its details are logged to
``models.EventLog``, stored in a separate database.

Anonymisation starts with ``models.PrivacyModel.anonymise``, which then calls
the field-specific anonymise functions in the ``PrivacyMeta`` instance; fields
which do not have one defined use ``anonymiser.anonymise_field``.


Known limitations
=================

* QuerySet bulk deletions on a model will not be detected unless it has a
  ``PrivacyMeta`` or is manually registered with ``gdpr_assist.register``
* Operations involving gdpr-assist may be slower than normal (ie bulk
  deletions) due to the additional processing required.


.. _roadmap:

Roadmap
=======

Features planned for future releases:

* Settings to customise the ``anonymised`` field name and ``anonymise()``
  method name on registered models - see :doc:`anonymising`
* Subclass the queryset of ``on_delete=ANONYMISE(..)`` related models which
  aren't registered, so that bulk deletion always results in anonymisation -
  see :doc:`anonymising`
* Ability to change a relationship field on a registered third-party model to
  use ``on_delete=ANONYMISE(..)``
* A generic view to allow self-service data export, ready to be added to
  user-facing profile management.
* A generic view to allow self-service data removal, ready to be added to
  user-facing profile management.

This app does not currently attempt to provide any sort of framework for managing opt-in or consent, because in our experience no two sites are similar enough for a generic solution.