==================
django-GDPR-assist
==================

Tools to help manage your users' data in the age of GDPR

https://github.com/wildfish/django-gdpr-assist

.. image:: https://travis-ci.org/wildfish/django-gdpr-assist.svg?branch=master
    :target: https://travis-ci.org/wildfish/django-gdpr-assist

.. image:: https://coveralls.io/repos/wildfish/django-gdpr-assist/badge.svg?branch=master&service=github
    :target: https://coveralls.io/github/wildfish/django-gdpr-assist?branch=master

.. image:: https://readthedocs.org/projects/django-gdpr-assist/badge/?version=latest
    :target: https://django-gdpr-assist.readthedocs.io/en/latest/?badge=latest

Features
========

* Find, export and anonymise personal data to comply with GDPR requests
* Track anonymisation and deletion of personal data to replay after restoring
  backups
* Anonymise all models to sanitise working copies of a production database

Supports Django 1.8 to 2.1, on 3.4+.

See the `full documentation <https://django-gdpr-assist.readthedocs.io>`_ for details
of how GDPR-assist works; in particular:

* `Installation <https://django-gdpr-assist.readthedocs.io/en/latest/installation.html>`_
  - how to install
* `Usage <https://django-gdpr-assist.readthedocs.io/en/latest/usage.html>`_
  - overview of how to use it with your project
* `Upgrading <https://django-gdpr-assist.readthedocs.io/en/latest/upgrading.html>`_
  - what has changed from previous versions and how to upgrade
* `Contributing <https://django-gdpr-assist.readthedocs.io/en/latest/contributing.html>`_
  - how to contribute to the project


Quickstart
==========

Install with ``pip install django-gdpr-assist``, add ``gdpr_assist`` to
Django's ``INSTALLED_APPS`` and add a ``gdpr_log`` definition to ``DATABASES``.

Then start adding privacy metadata to your models::

    class Comment(models.Model):
        name = models.CharField(max_length=255, blank=True)
        age = models.IntegerField(null=True, blank=True)
        message = models.TextField()

        class PrivacyMeta:
            fields = ['name', 'age']
            search_fields = ['name']
            export_fields = ['name', 'age', 'message']

This will allow you to anonymise and export data in this model using the
standard gdpr-assist admin tool. You can also configure anonymisation or
deletion of a related model to trigger anonymisation of your model, and can
manually register a ``PrivacyMeta`` for third-party models without modifying
their code.

Anonymisation and deletion events for models registered with gdpr-assist are
logged for replay after a backup restoration with the ``gdpr_rerun`` management
command. When you need to work with a copy of the production data, there is
also the ``anonymise_db`` command, which will anonymise the whole database.
