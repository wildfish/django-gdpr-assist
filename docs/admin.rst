==============
The admin site
==============

Bulk anonymisation
------------------

To add an "Anonymise" option to the actions list for a ``ModelAdmin``, subclass
``gdpr_assist.admin.ModelAdmin``::

    import gdpr_assist
    class MyAdmin(gdpr_assist.admin.ModelAdmin):
        ...
    admin.site.register(MyModel, MyAdmin)


Personal data tool
------------------

In the admin site, under ``GDPR``, select ``Personal data``. This is a tool
which lets you find, export, delete and anonymise personal data.

Submitting the search will call the ``PrivacyMeta.search()`` method on all
models registered with gdpr-assist.

From there, records can be selected for export, anonymisation or deletion.

This tool is only available to superusers.

