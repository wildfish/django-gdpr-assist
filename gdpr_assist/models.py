"""
Model-related functionality
"""
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from collections import defaultdict
from copy import copy
import six

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from . import app_settings
from . import handlers  # noqa
from .anonymiser import anonymise_field, anonymise_related_objects
from .signals import pre_anonymise, post_anonymise


class PrivacyQuerySet(models.query.QuerySet):
    """
    A QuerySet with support anonymising data
    """
    def anonymise(self, user=None):
        """
        Anonymise all privacy-registered objects in this queryset
        """
        for obj in self:
            obj.anonymise(force=True, user=user)

    def delete(self):
        """
        Anonymise privacy-registered objects related to this queryset
        """
        for obj in self:
            anonymise_related_objects(obj)

        super(PrivacyQuerySet, self).delete()

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
    fk_fields = []
    set_fields = []
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
                return lambda instance, user: anonymise_field(instance, field_name, user)
        raise AttributeError('Attribute {} not defined'.format(item))

    @cached_property
    def _anonymise_fields(self):
        if self.fields is None and self.fk_fields is None and self.set_fields is None:
            return [
                field.name for field in self.model._meta.get_fields()
                if field.name not in [self.model._meta.pk.name, 'anonymised']
            ]

        fields = self.fields or []
        all_fields = fields + self.fk_fields + self.set_fields

        return all_fields

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
    retention_policy = models.ForeignKey(
        to="gdpr_assist.RetentionPolicyItem", on_delete=models.SET_NULL,
        null=True, blank=True,
    )

    def anonymise(self, force=False, user=None):
        # Only anonymise things once to avoid a circular anonymisation
        if self.anonymised and not force:
            self._log_gdpr_already_anonymised(user)
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
            anonymiser(self, user)

        # Log the obj class and pk
        self._log_gdpr_anonymise(user)

        try:
            self.save()
        except ValidationError as e:
            self._log_gdpr_error(e, user)
            print(e)

        post_anonymise.send(sender=self.__class__, instance=self)

    def _log_gdpr_delete(self, user=None):
        EventLog.objects.log_delete(self, user)

    def _log_gdpr_anonymise(self, user=None):
        EventLog.objects.log_anonymise(self, user)

    def _log_gdpr_error(self, error, user=None):
        EventLog.objects.log_error(self, error, user)

    def _log_gdpr_recursive(self, user=None, start=True):
        EventLog.objects.log_recursive(self, user, start)

    def _log_gdpr_already_anonymised(self, user=None):
        EventLog.objects.log_already_anonymised(self, user)


    @classmethod
    def _cast_class(cls, model, privacy_meta):
        """
        Change the model to subclass PrivacyModel/

        Called automatically when a model is registered with the privacy registry

        Arguments:
            model   The model to turn into a PrivacyModel subclass.
        """
        # Make the model subclass PrivacyModel
        # If done this way, the model will NOT have a link to retention policy
        # To do that, make it an explicit subclass of PrivacyModel
        try:
            model.__bases__ = (PrivacyModel,) + model.__bases__

            # Tell the field it's now a member of the new model
            # We need to do this manually, as the base class has been added after
            # the class thinks it has been prepared
            field = copy(PrivacyModel._meta.get_field('anonymised'))
            field.contribute_to_class(model, 'anonymised')
        except TypeError:
            pass  # already an explicit subclass
        # Make the managers subclass PrivacyManager
        # TODO: loop through all managers
        if (
            hasattr(model, 'objects') and
            not issubclass(model.objects.__class__, PrivacyManager)
        ):
            PrivacyManager._cast_class(model.objects)

        return model

    def get_anonymisation_log(self):
        """
        See if there are any related models which need to be anonymised.

        They will be any reverse relations to PrivacyModel subclasses where their
        OneToOneField and ForeignKey on_delete is ANONYMISE.
        """
        if not self.anonymised:
            return "%s is not anonymised yet." % self

        logs = EventLog.objects.order_by('log_time')

        top_level_log_lines = EventLog.objects.for_instance(self).values('log_time', 'event', 'app_label', 'model_name',
                                                                        'target_pk', 'acting_user')

        if top_level_log_lines.count() > 0:
            actual_anon_log_line_start = top_level_log_lines.filter(event=EventLog.EVENT_RECURSIVE_START).last()
            actual_anon_log_line_end = top_level_log_lines.filter(event=EventLog.EVENT_ANONYMISE).last()

            lines = logs.filter(log_time__gte=actual_anon_log_line_start["log_time"],
                                log_time__lte=actual_anon_log_line_end["log_time"]). \
                values('log_time', 'event', 'app_label', 'model_name', 'target_pk', 'acting_user')

            user = actual_anon_log_line_start["acting_user"] or "[Non-descript user]"

            res = "{model_name} #{target_pk} starting to anonymise [by {user} on {log_time}].\n".format(
                model_name=actual_anon_log_line_start['model_name'],
                target_pk=actual_anon_log_line_start['target_pk'],
                user=user,
                log_time=actual_anon_log_line_start["log_time"].strftime("%Y-%m-%d %H:%M:%S"),
            )
            indent_level = 0

            def tabify(x):
                return "\t" * x if x > 0 else ""

            for l in lines:
                if l["event"] == EventLog.EVENT_RECURSIVE_START:
                    res += "%sStarting recursive for %s #%s.\n" % (
                    tabify(indent_level), l['model_name'], l['target_pk'])
                    indent_level += 1

                elif l["event"] == EventLog.EVENT_RECURSIVE_END:
                    indent_level -= 1
                    res += "%sEnding recursive for %s #%s.\n" % (tabify(indent_level), l['model_name'], l['target_pk'])

                elif l["event"] == EventLog.EVENT_ALREADY_ANONYMISED:
                    res += "%s%s #%s already anonymised.\n" % (tabify(indent_level), l['model_name'], l['target_pk'])

                else:
                    res += "%s%s #%s flat fields anonymised.\n" % (
                    tabify(indent_level), l['model_name'], l['target_pk'])

            return res
        else:
            return "%s is anonymised, but does not have matching logs." % self

    @classmethod
    def get_anonymisation_tree(cls, prefix="", doprint=False, objs=[]):
        """
        Print the result of the nesting defined above for a given model.
        Useful for sanity and loop checking. Example output:

        Class:
        |-> outcome_assessments = (OutcomeAssessment [set_field]):
            |-> score
            |-> comment
        |-> class_polls = (ClassPoll [set_field]):
            |-> poll = (Poll [fk]):
                |-> title
                |-> question
                |-> pollchoice_set = (PollChoice [set_field]):
                    |-> choice
                |-> pollsession_set = (PollSession [set_field]):
                    |-> outcome_assessments = (OutcomeAssessment [set_field]):
                        |-> score
                        |-> comment
                    |-> pollresponse_set = (PollResponse [set_field]):
                        |-> response

        """
        ABANDON_AFTER_N_LEVELS = 10
        BASE_PREFIX = "    "
        if len(prefix) > len(BASE_PREFIX) * ABANDON_AFTER_N_LEVELS:
            return "ERROR: shouldn't go %s levels deep, check for loops." % ABANDON_AFTER_N_LEVELS
        res = ''
        if doprint:
            res += cls.__name__ + ":\n"

        privacy_meta_model = cls._privacy_meta

        flat_fields = privacy_meta_model.fields
        if flat_fields:
            for f in flat_fields:
                res += "%s|-> %s\n" % (prefix, f)

        for fk in privacy_meta_model.fk_fields:

            try:
                f = getattr(cls, fk)
                if hasattr(f, 'field'):
                    f = f.field
                elif hasattr(f, 'rel'):
                    f = f.rel
                child_model = f.related_model
                res += "%s|-> %s = (%s [fk]):\n" % (prefix, fk, child_model.__name__)

                res += child_model.get_anonymization_tree(prefix=BASE_PREFIX + prefix, doprint=False)
            except AttributeError as e:
                print(e)
                res += 'ERROR: ' + str(e)

        for set_field in privacy_meta_model.set_fields:
            res += "%s|-> %s" % (prefix, set_field)

            try:
                f = getattr(cls, set_field)
                if hasattr(f, "objects"):
                    child_model = f.objects.model
                elif hasattr(f, "rel"):
                    child_model = f.rel.related_model
                res += " = (%s [set_field]):\n" % child_model.__name__
                res += child_model.get_anonymization_tree(prefix=BASE_PREFIX + prefix, doprint=False)
            except AttributeError as e:
                print(e)
                res += 'ERROR: ' + str(e)

        if doprint:
            print(res)
        return res

    class Meta:
        abstract = True


@python_2_unicode_compatible
class RetentionPolicyItem(PrivacyModel):
    description = models.CharField(default="", max_length=255)
    start_date = models.DateTimeField(null=True, blank=False)
    updated_at = models.DateTimeField(auto_now=True)
    policy_length = models.DurationField(null=True, blank=True)  # corresponds to a datetime.timedelta
    retention_policy = None  # it would inherit this from PrivacyModel, but it doesn't make sense here

    def list_related_objects(self):
        return [
            related_object
            for related_object in getattr(self, field).all()
            for field in self._meta.get_fields()
            if field.is_relation and field.one_to_many
        ]

    def should_be_anonymized(self):
        if self.policy_length is None:
            return False

        return timezone.now() > self.start_date + self.policy_length

    def __str__(self):
        if self.description:
            return self.description

        return "Retention Policy %s starts %s days after %s" % (self.id, self.start_date, self.policy_length)

    @classmethod
    def get_anonymization_tree(cls, prefix="", doprint=False, objs=None):
        """
        The anonymization tree for a retention policy should show the number
        of objects about to be anonymized.
        """
        if objs is None:
            objs = []

        # Flat list of related objects
        related_objects_by_class = defaultdict(list)

        for obj in objs:
            for related_object in obj.list_related_objects():
                related_objects_by_class[related_object.__class__].append(related_object)

        tree_html = ""
        for class_, related_objects in related_objects_by_class.items():
            tree = class_.get_anonymization_tree()  # possibly surface this info (what will be anonymized by class

            # summarize the first 10
            related_objects_summaries = [
                "<li>{related_object}</li>".format(related_object=related_object)
                for related_object in related_objects[:10]
            ]

            if len(related_objects) > 10:
                related_objects_summaries.append('<li style="list-style-type: none;">...</li>')

            tree_html += (
                '<br/><b title="{tree}">{class_name}</b> ({related_objects_count})<ul>{summaries}</ul>\n'.format(
                    tree=tree,
                    class_name=c.__name__,
                    related_objects_count=len(objs),
                    summaries="\n".join(related_objects_summaries),
                )
            )

        return mark_safe(tree_html)


class EventLogManager(models.Manager):
    def for_instance(self, instance, user=None):
        cls = instance.__class__

        loglines = self.filter(
            app_label=cls._meta.app_label,
            model_name=cls._meta.object_name,
            target_pk=instance.pk,
        )

        if user is not None:
            loglines = loglines.filter(user=user)

        return loglines

    def log_delete(self, instance, user=None):
        self.log(self.model.EVENT_DELETE, instance, user)

    def log_anonymise(self, instance, user=None):
        self.log(self.model.EVENT_ANONYMISE, instance, user)

    def log_recursive(self, instance, user=None, start=True):
        if start:
            self.log(self.model.EVENT_RECURSIVE_START, instance, user)
        else:
            self.log(self.model.EVENT_RECURSIVE_END, instance, user)

    def log_already_anonymised(self, instance, user=None):
        self.log(self.model.EVENT_ALREADY_ANONYMISED, instance, user)

    def log_error(self, instance, error, user=None):
        """
        Add an error_message to the last log line that matches this instance.
        """
        cls = instance.__class__

        loglines = self.for_instance(instance, user=user)

        if loglines.count() > 0:
            logline = loglines.last()
            logline.error_message = str(error)
            logline.save()
        else:
            # TODO throw an error? maybe create this message with an error?
            print("Cannot log an error for %s.%s pk=%s, since there is no existing log message" % (cls._meta.app_label, cls._meta.object_name, instance.pk))

    def log(self, event, instance, user=None):
        cls = instance.__class__
        self.create(
            event=event,
            app_label=cls._meta.app_label,
            model_name=cls._meta.object_name,
            target_pk=instance.pk,
            acting_user=str(user)
        )


class EventLog(models.Model):
    EVENT_DELETE = 'delete'
    EVENT_ANONYMISE = 'anonymise'
    EVENT_RECURSIVE_START = 'anonymisation recursion start'
    EVENT_RECURSIVE_END = 'anonymisation recursion end'
    EVENT_ALREADY_ANONYMISED = 'anonymisation abandoned, already done'
    EVENT_CHOICES = (
        (EVENT_DELETE, _("Delete")),
        (EVENT_ANONYMISE, _("Anonymise")),
        (EVENT_RECURSIVE_START, _("Anonymisation Recursion Start")),
        (EVENT_RECURSIVE_END, _("Anonymisation Recursion End")),
        (EVENT_ALREADY_ANONYMISED, _('Anonymisation Skipped, Already Done'))
    )

    event = models.CharField(
        max_length=max((len(k) for k, v in EVENT_CHOICES)),
        choices=EVENT_CHOICES,
    )
    app_label = models.CharField(max_length=255)
    model_name = models.CharField(max_length=255)
    log_time = models.DateTimeField(auto_now_add=True)
    acting_user = models.CharField(max_length=255, default="")
    error_message = models.CharField(max_length=1000, default=None, null=True, blank=True)
    target_pk = models.TextField()

    objects = EventLogManager()

    def get_target(self):
        model = apps.get_model(self.app_label, self.model_name)
        try:
            obj = model._base_manager.get(pk=self.target_pk)
        except model.DoesNotExist:
            return None
        return obj

    def summary(self):
        return "{log_time}: {event} performed on {model_name} {target_pk} (app {app_label}) [{acting_user}]".format(
            log_time=self.log_time,
            event=self.event,
            model_name=self.model_name,
            target_pk=self.target_pk,
            app_label=self.app_label,
            acting_user=self.acting_user,
        )
