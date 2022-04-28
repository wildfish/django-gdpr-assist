=========
Upgrading
=========

For an overview of what has changed between versions, see the :ref:`changelog`.


Instructions
============


Upgrading from 1.1.0
--------------------

Anonymisation flag
::::::::::::::::::

Version 1.2.0 changes the way the anonymisation flag is stored. Previously it was stored
in an ``anonymised`` field which gdpr-assist added to your models, but this caused
problems when wanting to anonymise third party models. This flag has now been moved to a
new model in the gdpr-assist app, linked to your objects using a generic foreign key.

If you migrate without following these instructions, you will lose information about
which database objects have been anonymised.


Migrating your data
...................

You must write a data migration to move this data to run before you create a migration
to remove the ``anonymised`` field. There is a migration operator to help you:

1. Create empty migrations for your apps with existing anonymisable models::

        ./manage.py makemigrations myapp --empty

2. Add the operator using the following migration template::


        from django.db.migrations import Migration
        from gdpr_assist.upgrading import MigrateGdprAnonymised

        class Migration(migrations.Migration):
            dependencies = [
                ('myapp', '0012_migration'),  # Added by makemigrations
                ('gdpr_assist', '0002_privacyanonymised'),  # Keep this dependency
            ]
            operations = [
                MigrateGdprAnonymised('MyModelOne'),  # Update this to your model
                MigrateGdprAnonymised('MyModelSix'),  # Repeat for all your GDPR models
            ]

3. Create migrations to remove the fields::

        ./manage.py makemigrations myapp

4. Repeat for any other apps with anonymisable models

5. Run all migrations

        ./manage.py migrate

        ./manage.py migrate --database=gdpr_log


System check gdpr_assist.E001
.............................

Version 1.2.0 onwards adds a system check to ensure you have followed the above
instructions, to avoid accidental data loss when upgrading. If your migration tries to
remove the field before you have migrated data, you will see the error message::

    Removing anonymised field before its data is migrated

This is triggered when removing any field called ``anonymised`` before it has been
migrated with the ``MigrateGdprAnonymised`` operator.

In most cases you can fix this by following the instructions above.

If the ``anonymised`` field was not added by gdpr-assist, and you do not want to run
``MigrateGdprAnonymised``, you can tell the check to ignore the failing migration by
adding ``gdpr_assist_safe = True`` to the migration class; for example::

    class Migration(migrations.Migration):
        gdpr_assist_safe = True
        dependencies = [...

Alternatively if you are happy that all your migrations are safe, you can add the check
to ``SILENCED_SYSTEM_CHECKS`` in your project settings to disable the migration check::

    SILENCED_SYSTEM_CHECKS = [
        "gdpr_assist.E001",
    ]


Changes to your code
....................

In most cases no further action will be required, but if you are using the
``anonymised`` field in your own code, you will need to call ``is_anonymised()`` or
query the model ``gdpr_assist.models.PrivacyAnonymised`` instead.


.. _changelog:

Changelog
=========

1.4.2, 2022-04-28
-----------------

Fix admin styling issue on person search.

1.4.1, 2022-02-25
-----------------

Fix migration issue caused in supporting 2.2/without default_auto_field. Thanks @mserrano07 @llexical.

1.4.0, 2022-01-19
-----------------

Features:

* Add support for Django 3.2, 4.0.
* Updated example project.
* Improve performance of log database and added ``GDPR_LOG_ON_ANONYMISE`` option to disable logging.

Fix:

* Resolve issue 48, use_in_migrations. Managers with use_in_migrations=True will no longer be cast, instead a
duplicate is created using the name provided at register(..., gdpr_default_manager_name="abc").
* Update PrivacyModel cast to support inheriting from another privacy model.
* Performance improvements to for management command thanks @jayaddison-collabora

1.3.0, 2020-08-14
-----------------

Features:

* Add support for Django 3.0 and 3.1


Changes:

* Remove support for Django 2.1 and earlier


1.2.0, 2020-07-15
-----------------

Features:

* Add support for Django 2.2
* Add ``can_anonymise`` flag to ``PrivacyMeta`` to support searching and exporting data
  which shouldn't be anonymised. (#15, #17)
* Add bulk anonymisation operations to improve efficiency of large anonymisations


Changes:

* Remove support for Django 1.8


Bugfixes:

* Fix support for third party models by removing the ``anonymised`` field (#5, #13)
* Fix duplicate migrations (#6, #12)
* Fix documentation for post_anonymise (#8, #14)


Internal:

* Code style updated to use black and isort


1.1.0, 2020-03-20
-----------------

Bugfix:

* Allow managers with delete to have custom additional parameters.


Other:

* This version removes python 2.7 support.


1.0.1, 2018-10-23
-----------------

Bugfix:

* Managers on registered models which set ``use_in_migrations`` can now be
  serialised for migrations.


1.0.0, 2018-09-16
-----------------

Initial public release
