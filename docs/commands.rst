========
Commands
========


Re-running deletions and anonymisations
=======================================

To re-run a set of deletions and anonymisations, make sure your log database is
available, then run::

    ./manage.py gdpr_rerun


Anonymising all personal data
=============================

To anonymise all data in all models registered with gdpr-assist::

    ./manage.py anonymise_db

This will anonymise all data in the database,

This command can be useful when working on a stage or local copy of the live
database. Because it is probably a bad idea to run this on a production
database, you will need to enable this command with the setting
``GDPR_CAN_ANONYMISE_DATABASE = True``.
