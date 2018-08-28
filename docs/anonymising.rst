===================
Anonymising objects
===================

Model changes
=============

Once a model has been registered with gdpr-assist, its instances will have
some additional attributes:


``obj.anonymised = BooleanField()``
-----------------------------------

This is a boolean value stored in the database to register whether the object
has been anonymised or not.


``obj.anonymise()``
-------------------

Call this to anonymise the private fields on the object.


How anonymisation works
=======================

If a field is nullable, the value will be set to ``None`` (or in the case of
blankable strings, ``''``).

If a field is not nullable, the value will be set to a sensible default:

* Numbers will be set to ``0``
* Strings will be set to a string representation of the primary key field
* Booleans will be set to ``False`` (although ``NullBooleanField`` will always
  be nullable)
* ``DateField`` and ``DateTimeField`` will be set to the current date and time
* ``TimeField`` will be set to ``00:00``
* ``DurationField`` will be set to ``timedelta(0)``
* ``EmailField`` will be anonymised to ``{pk}@anon.example.com``
* ``URLField`` will be anonymised to ``{pk}@anon.example.com``
* ``GenericIPAddressField`` will be set to ``0.0.0.0``
* ``UUIDField`` will be set to ``{00000000-0000-0000-0000-000000000000}``

These default actions can be overridden by defining a custom anonymiser as
``anonymise_<field_name>`` method on the ``PrivacyMeta`` class - see the
:doc:`PrivacyMeta <privacy_meta>` documentation  for more details.

Custom field types will also need a custom anonymiser to be defined.

Some fields cannot be anonymised unless they can be null, and trying to
anonymise them without a custom anonymiser will raise a
``gdpr_assist.AnonymiseError`` exception:

* File fields (``FilePathField``, ``FileField``, ``ImageField``)
* Relationships (``OneToOneField``, ``ForeignKey``)

To ensure data integrity, trying to anonymise a ``ManyToManyField`` will always
raise a ``gdpr_assist.AnonymiseError``, unless you are using a custom
anonymiser for that field.

The anonymiser cannot anonymise the primary key.


Anonymising related objects
===========================

When anonymising an object, its related objects will not be anonymised
automatically. This is to prevent unintentional side-effects.


Using signals
-------------

To cascade an anonymisation to another model, use signals:


``gdpr_assist.signals.pre_anonymise``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Called before the object is anonymised. You will be passed the original object.

Example::

    from gdpr_assist.signals import pre_anonymise

    @receiver(pre_anonymise, sender=MyModel)
    def anonymise_related(sender, instance):
        instance.my_related_obj.anonymise()


``gdpr_assist.signals.post_anonymise``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Called after anonymisation of the object. You will be passed the anonymised
object.

Example::

    from gdpr_assist.signals import pre_anonymise

    @receiver(pre_anonymise, sender=MyModel)
    def anonymise_related(sender, instance):
        instance.my_related_obj.anonymise()


When deleting an object
-----------------------

When an object is deleted, any objects related to the object as
``on_delete=gdpr_assist.ANONYMISE(..)`` will be anonymised. This takes
one argument - the type of ``on_delete`` to perform on the field itself; for
example::

    class MyModel(models.Model):
        fk = models.ForeignKey(
            TargetModel,
            on_delete=gdpr_assist.ANONYMISE(models.SET_NULL),
        )

``ANONYMISE(..)`` cannot take ``CASCADE`` or ``PROTECTED`` as arguments.


Deleting querysets
~~~~~~~~~~~~~~~~~~

gdpr-assist modifies the queryset of registered models so that a bulk deletion
will anonymise any related objects which use ``ANONYMISE(..)``.

Note that Django does not send delete signals for bulk delete operations in
other for situations, so to anonymise related objects when a queryset is
deleted, make sure the model being deleted is registered with gdpr-assist.
