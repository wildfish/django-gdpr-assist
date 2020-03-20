"""
Model-related functionality
"""
from copy import copy
import six

from django.apps import apps
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.functional import cached_property

from . import app_settings
from . import handlers  # noqa
from .anonymiser import anonymise_field, anonymise_related_objects
from .signals import pre_anonymise, post_anonymise


class PrivacyQuerySet(models.query.QuerySet):
    """
    A QuerySet with support anonymising data
    """
    def anonymise(self):
        """
        Anonymise all privacy-registered objects in this queryset
        """
        for obj in self:
            obj.anonymise()

    def delete(self, *args, **kwargs):
        """
        Anonymise privacy-registered objects related to this queryset
        """
        for obj in self:
            anonymise_related_objects(obj)

        super(PrivacyQuerySet, self).delete(*args, **kwargs)

    @classmethod
    def _cast_class(cls, queryset):
        """
        Changes the class of the specified queryset to a subclass of PrivacyQuerySet
        and the original class, so it has all the same properties it did when it
        was first initialised, but is now a PrivacyQuerySet subclass.
        The new class is given the same name as the old class, but with the prefix
        'CastPrivacy' to indicate the type of the object has changed, eg a normal
        QuerySet will become CastPrivacyQuerySet.
        """
        # Make a subclass of PrivacyQuerySet and the original class
        orig_cls = queryset.__class__
        queryset.__class__ = type(
            str('CastPrivacy{}'.format(orig_cls.__name__)), (cls, orig_cls), {},
        )
        return queryset


class PrivacyManager(models.Manager):
    """
    A manager with support for anonymising data

    Don't subclass this directly - write your manager as normal, this will be
    applied automatically.
    """
    # The class of a privacy queryset.
    privacy_queryset = PrivacyQuerySet

    def _enhance_queryset(self, qs):
        """
        Enhance an existing queryset with the class in self.privacy_queryset
        """
        return self.privacy_queryset._cast_class(qs)

    def get_queryset(self, *args, **kwargs):
        """
        Get the original queryset and then enhance it
        """
        qs = super(PrivacyManager, self).get_queryset(*args, **kwargs)
        return self._enhance_queryset(qs)

    @classmethod
    def _cast_class(cls, manager):
        """
        Changes the class of the specified manager to a subclass of PrivacyManager
        and the original class, so it has all the same properties it did when it
        was first initialised, but is now a PrivacyManager subclass.
        The new class is given the same name as the old class, but with the prefix
        'CastPrivacy' to indicate the type of the object has changed, eg a normal
        Manager will become CastPrivacyManager
        """
        # Make a subclass of PrivacyQuerySet and the original class
        orig_cls = manager.__class__
        manager.__class__ = type(
            str('CastPrivacy{}'.format(orig_cls.__name__)), (cls, orig_cls), {},
        )
        return manager

    def deconstruct(self):
        """
        Deconstruct the original manager - it will be cast again next time.
        """
        # Check bases are as expected from _cast_class
        bases = self.__class__.__bases__
        if len(bases) != 2:  # pragma: no cover
            raise ValueError('Unexpected base classes for CastPrivacyManager')

        # Original is second - instatiate and deconstruct it
        orig_cls = bases[1]
        orig_args = self._constructor_args[0]
        orig_kwargs = self._constructor_args[1]
        orig_manager = orig_cls(*orig_args, **orig_kwargs)
        return orig_manager.deconstruct()


class PrivacyMeta(object):
    fields = None
    search_fields = None
    export_fields = None
    export_exclude = None
    export_filename = None

    def __init__(self, model):
        self.model = model

    def __getattr__(self, item):
        """
        Handle anonymisation of private fields that don't have a custom
        anonymiser
        """
        if item.startswith('anonymise_'):
            field_name = item[len('anonymise_'):]
            if field_name in self._anonymise_fields:
                return lambda instance: anonymise_field(instance, field_name)
        raise AttributeError('Attribute {} not defined'.format(item))

    @cached_property
    def _anonymise_fields(self):
        if self.fields is None:
            return [
                field.name for field in self.model._meta.get_fields()
                if field.name not in [self.model._meta.pk.name, 'anonymised']
            ]
        return self.fields

    def search(self, term):
        """
        Subclasses should implement this
        """
        if not self.search_fields:
            return self.model.objects.none()

        query = {}
        for field_name in self.search_fields:
            if '__' not in field_name:
                field_name = '{}__iexact'.format(field_name)
            query[field_name] = term
        return self.model.objects.filter(**query)

    @cached_property
    def _export_fields(self):
        export_fields = self.export_fields or [
            field.name for field in self.model._meta.get_fields()
            if (
                (not field.auto_created or field.concrete) and
                field.name not in [self.model._meta.pk.name, 'anonymised']
            )
        ]
        if self.export_exclude:
            export_fields = set(export_fields).difference(self.export_exclude)
        return export_fields

    def export(self, instance):
        return {
            field_name: six.text_type(getattr(instance, field_name))
            for field_name in self._export_fields
        }

    def get_export_filename(self):
        if self.export_filename is not None:
            return self.export_filename
        return '{}-{}.csv'.format(
            self.model._meta.app_label,
            self.model._meta.object_name,
        )


class PrivacyModel(models.Model):
    """
    An abstract model base class with support for anonymising data
    """
    anonymised = models.BooleanField(default=False)

    def anonymise(self, force=False):
        # Only anonymise things once to avoid a circular anonymisation
        if self.anonymised and not force:
            return

        pre_anonymise.send(sender=self.__class__, instance=self)

        # Anonymise data
        self.anonymised = True
        privacy_meta = getattr(self, app_settings.GDPR_PRIVACY_INSTANCE_NAME)
        for field_name in privacy_meta._anonymise_fields:
            anonymiser = getattr(
                privacy_meta,
                'anonymise_{}'.format(field_name),
            )
            anonymiser(self)

        # Log the obj class and pk
        self._log_gdpr_anonymise()

        self.save()
        post_anonymise.send(sender=self.__class__, instance=self)

    def _log_gdpr_delete(self):
        EventLog.objects.log_delete(self)

    def _log_gdpr_anonymise(self):
        EventLog.objects.log_anonymise(self)

    @classmethod
    def _cast_class(cls, model, privacy_meta):
        """
        Change the model to subclass PrivacyModel/

        Called automatically when a model is registered with the privacy registry

        Arguments:
            model   The model to turn into a PrivacyModel subclass.
        """
        # Make the model subclass PrivacyModel
        model.__bases__ = (PrivacyModel,) + model.__bases__

        # Tell the field it's now a member of the new model
        # We need to do this manually, as the base class has been added after
        # the class thinks it has been prepared
        field = copy(PrivacyModel._meta.get_field('anonymised'))
        field.contribute_to_class(model, 'anonymised')

        # Make the managers subclass PrivacyManager
        # TODO: loop through all managers
        if (
            hasattr(model, 'objects') and
            not issubclass(model.objects.__class__, PrivacyManager)
        ):
            PrivacyManager._cast_class(model.objects)

        return model

    class Meta:
        abstract = True


class EventLogManager(models.Manager):
    def log_delete(self, instance):
        self.log(self.model.EVENT_DELETE, instance)

    def log_anonymise(self, instance):
        self.log(self.model.EVENT_ANONYMISE, instance)

    def log(self, event, instance):
        cls = instance.__class__
        self.create(
            event=event,
            app_label=cls._meta.app_label,
            model_name=cls._meta.object_name,
            target_pk=instance.pk,
        )


class EventLog(models.Model):
    EVENT_DELETE = 'delete'
    EVENT_ANONYMISE = 'anonymise'
    EVENT_CHOICES = (
        (EVENT_DELETE, _("Delete")),
        (EVENT_ANONYMISE, _("Anonymise")),
    )

    event = models.CharField(
        max_length=max((len(k) for k, v in EVENT_CHOICES)),
        choices=EVENT_CHOICES,
    )
    app_label = models.CharField(max_length=255)
    model_name = models.CharField(max_length=255)
    target_pk = models.TextField()

    objects = EventLogManager()

    def get_target(self):
        model = apps.get_model(self.app_label, self.model_name)
        try:
            obj = model._base_manager.get(pk=self.target_pk)
        except model.DoesNotExist:
            return None
        return obj
