"""
Model-related functionality
"""
import sys
from copy import copy, deepcopy

from django.apps import apps
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from . import handlers  # noqa
from . import app_settings
from .anonymiser import anonymise_field, anonymise_related_objects
from .cast import cast_instance
from .signals import post_anonymise, pre_anonymise


class PrivacyQuerySet(models.query.QuerySet):
    """
    A QuerySet with support anonymising data
    """

    def anonymise(self, for_bulk=True):
        """
        Anonymise all privacy-registered objects in this queryset
        """
        # Abandon if we can't anonymise
        if not getattr(
            self.model, app_settings.GDPR_PRIVACY_INSTANCE_NAME
        ).can_anonymise:
            return

        bulk_objects = []
        bulk_log_objects = []
        for obj in self:
            privacy_obj = obj.anonymise(for_bulk=for_bulk)
            if privacy_obj:
                bulk_objects.append(privacy_obj)
                if hasattr(privacy_obj, "_log_obj"):
                    bulk_log_objects.append(privacy_obj._log_obj)

        if bulk_objects and for_bulk:
            PrivacyAnonymised.objects.bulk_create(bulk_objects)
            if bulk_log_objects:
                EventLog.objects.bulk_create(bulk_log_objects)

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
        cast_instance(queryset, cls)
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
        qs = qs.prefetch_related("anonymised_relation")
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

        Also add the new manager to the module, so it can be imported for migrations.
        """
        # Make a subclass of PrivacyQuerySet and the original class
        cast_instance(manager, cls)
        return manager


class PrivacyMeta(object):
    can_anonymise = True
    fields = None
    search_fields = None
    export_fields = None
    export_exclude = None
    export_filename = None
    gdpr_default_manager_name = None

    def __init__(self, model, gdpr_default_manager_name=None):
        self.model = model
        self.gdpr_default_manager_name = gdpr_default_manager_name if gdpr_default_manager_name else "objects"

    def __getattr__(self, item):
        """
        Handle anonymisation of private fields that don't have a custom
        anonymiser
        """
        if item.startswith("anonymise_"):
            field_name = item[len("anonymise_") :]
            if field_name in self._anonymise_fields:
                return lambda instance: anonymise_field(instance, field_name)
        raise AttributeError("Attribute {} not defined".format(item))

    @cached_property
    def _anonymise_fields(self):
        if self.fields is None:
            return [
                field.name
                for field in self.model._meta.get_fields()
                if field.name not in [self.model._meta.pk.name, "anonymised_relation"]
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
            if "__" not in field_name:
                field_name = "{}__iexact".format(field_name)
            query[field_name] = term
        return self.model.objects.filter(**query)

    @cached_property
    def _export_fields(self):
        export_fields = self.export_fields or [
            field.name
            for field in self.model._meta.get_fields()
            if (
                (not field.auto_created or field.concrete)
                and field.name not in [self.model._meta.pk.name, "anonymised_relation"]
            )
        ]
        if self.export_exclude:
            export_fields = set(export_fields).difference(self.export_exclude)
        return export_fields

    def export(self, instance):
        return {
            field_name: str(getattr(instance, field_name))
            for field_name in self._export_fields
        }

    def get_export_filename(self):
        if self.export_filename is not None:
            return self.export_filename
        return "{}-{}.csv".format(
            self.model._meta.app_label, self.model._meta.object_name
        )


class PrivacyAnonymised(models.Model):
    """
        object_id is CharField so we can support models which are UUID pks based also.

        Django supports object_id being of a different type to the related object -
        https://docs.djangoproject.com/en/3.1/ref/contrib/contenttypes/#generic-relations
    """
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=36)
    anonymised_object = GenericForeignKey("content_type", "object_id")


class PrivacyModel(models.Model):
    """
        An abstract model base class with support for anonymising data.
    """

    anonymised_relation = GenericRelation(PrivacyAnonymised)

    @classmethod
    def get_privacy_meta(cls):
        return getattr(cls, app_settings.GDPR_PRIVACY_INSTANCE_NAME)

    @classmethod
    def check_can_anonymise(cls):
        return cls.get_privacy_meta().can_anonymise

    @classmethod
    def anonymisable_manager(cls):
        name = cls.get_privacy_meta().gdpr_default_manager_name
        return getattr(cls, name)

    def anonymise(self, force=False, for_bulk=False):
        privacy_meta = self.get_privacy_meta()

        # Only anonymise if allowed
        if not self.check_can_anonymise():
            return

        # Only anonymise things once to avoid a circular anonymisation
        if not force and self.is_anonymised():
            return

        pre_anonymise.send(sender=self.__class__, instance=self)

        # Anonymise data
        privacy_obj = PrivacyAnonymised(anonymised_object=self)

        if not for_bulk:
            privacy_obj.save()

        for field_name in privacy_meta._anonymise_fields:
            anonymiser = getattr(privacy_meta, "anonymise_{}".format(field_name))
            anonymiser(self)

        if app_settings.GDPR_LOG_ON_ANONYMISE:
            # Log the obj class and pk
            log_obj = self._log_gdpr_anonymise(for_bulk=for_bulk)

            if for_bulk:
                privacy_obj._log_obj = log_obj

        # TODO - we don't bulk save the objects being anonymised as they could send signals. However,
        # we possibly check this or perhaps provide an override setting for large anonymisations.
        self.save()
        post_anonymise.send(sender=self.__class__, instance=self)

        return privacy_obj

    def is_anonymised(self):
        return self.anonymised_relation.exists()

    def _log_gdpr_delete(self):
        EventLog.objects.log_delete(self)

    def _log_gdpr_anonymise(self, for_bulk=False):
        return EventLog.objects.log_anonymise(self, for_bulk=for_bulk)

    @classmethod
    def _cast_class(cls, model, privacy_meta):
        """
        Change the model to subclass PrivacyModel/

        Called automatically when a model is registered with the privacy registry

        Arguments:
            model   The model to turn into a PrivacyModel subclass.
        """
        # Make the model subclass PrivacyModel
        # If model does not already inherit from PrivacyModel via a parent only.
        if PrivacyModel not in model.mro():
            model.__bases__ = (PrivacyModel,) + model.__bases__

        # Tell the field it's now a member of the new model
        # We need to do this manually, as the base class has been added after
        # the class thinks it has been prepared
        field = copy(PrivacyModel._meta.get_field("anonymised_relation"))
        field.contribute_to_class(model, "anonymised_relation")

        gdpr_default_manager_name = privacy_meta.gdpr_default_manager_name

        # Make the managers subclass PrivacyManager
        # TODO: loop through all managers
        if hasattr(model, "objects") and not issubclass(
            model.objects.__class__, PrivacyManager
        ):
            to_cast = model.objects
            if to_cast.use_in_migrations and gdpr_default_manager_name == "objects":
                raise RuntimeError(f"Registered gdpr_assist model {model.__name__}s manager "
                                   "specified 'use_in_migrations=True', with no name provided.")

            # copy the manager to the defined name.
            setattr(model, gdpr_default_manager_name, deepcopy(to_cast))

            # if used in migrations, disable for the copy.
            if to_cast.use_in_migrations:
                setattr(getattr(model, gdpr_default_manager_name), "use_in_migrations", True)

            # cast the copied manager, if name is defaults, it will override.
            to_cast = getattr(model, gdpr_default_manager_name)

            PrivacyManager._cast_class(to_cast)

        return model

    class Meta:
        abstract = True


class EventLogManager(models.Manager):
    def log_delete(self, instance):
        self.log(self.model.EVENT_DELETE, instance)

    def log_anonymise(self, instance, for_bulk=False):
        obj = self.log(self.model.EVENT_ANONYMISE, instance, for_bulk=for_bulk)
        return obj

    def log(self, event, instance, for_bulk=False):
        cls = instance.__class__
        kwargs = {
            "event": event,
            "app_label": cls._meta.app_label,
            "model_name": cls._meta.object_name,
            "target_pk": instance.pk
        }
        if for_bulk:
            return self.model(**kwargs)
        else:
            return self.create(**kwargs)


class EventLog(models.Model):
    EVENT_DELETE = "delete"
    EVENT_ANONYMISE = "anonymise"
    EVENT_CHOICES = ((EVENT_DELETE, _("Delete")), (EVENT_ANONYMISE, _("Anonymise")))

    event = models.CharField(
        max_length=max((len(k) for k, v in EVENT_CHOICES)), choices=EVENT_CHOICES
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
