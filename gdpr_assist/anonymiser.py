"""
Anonymisation functionality
"""
import datetime
import uuid

from django.db import models
from django.utils.timezone import now

from .deletion import ANONYMISE
from .exceptions import AnonymiseError
from .registry import registry
from .app_settings import GDPR_PRIVACY_INSTANCE_NAME

anonymisers = {}


def register(*field_classes):
    def outer(fn):
        # Register function
        for cls in field_classes:
            anonymisers[cls] = fn

        return fn

    return outer


@register(
    models.BigIntegerField,
    models.IntegerField,
    models.PositiveIntegerField,
    models.PositiveSmallIntegerField,
    models.SmallIntegerField,
)
def anonymise_int(instance, field_name, field, value, user):
    if field.null:
        return None
    return 0


@register(
    models.CharField,
    models.SlugField,
    models.TextField,
)
def anonymise_char(instance, field_name, field, value, user):
    if field.blank and not field._unique:
        return ''
    return str(instance.pk)


@register(
    models.BinaryField,
)
def anonymise_binary(instance, field_name, field, value, user):
    if field.null:
        return None
    return b''


@register(
    models.BooleanField,
    models.NullBooleanField,
)
def anonymise_boolean(instance, field_name, field, value, user):
    if field.null:
        return None
    return False


@register(
    models.DateField,
)
def anonymise_date(instance, field_name, field, value, user):
    if field.null:
        return None
    return datetime.date.today()


@register(
    models.DateTimeField,
)
def anonymise_datetime(instance, field_name, field, value, user):
    if field.null:
        return None
    return now()


@register(
    models.TimeField,
)
def anonymise_time(instance, field_name, field, value, user):
    if field.null:
        return None
    return datetime.time()


@register(
    models.DurationField,
)
def anonymise_duration(instance, field_name, field, value, user):
    if field.null:
        return None
    return datetime.timedelta(0)


@register(
    models.DecimalField,
    models.FloatField,
)
def anonymise_decimal(instance, field_name, field, value, user):
    if field.null:
        return None
    return 0


@register(
    models.FileField,
    models.FilePathField,
    models.ImageField,
)
def anonymise_file(instance, field_name, field, value, user):
    if field.null:
        return None

    raise AnonymiseError(
        'Cannot anonymise {} - can only null file fields'.format(
            field_name,
        )
    )


@register(
    models.EmailField,
)
def anonymise_email(instance, field_name, field, value, user):
    if field.null:
        return None

    return '{}@anon.example.com'.format(instance.pk)


@register(
    models.GenericIPAddressField,
)
def anonymise_ip(instance, field_name, field, value, user):
    if field.null:
        return None

    return '0.0.0.0'


@register(
    models.URLField,
)
def anonymise_url(instance, field_name, field, value, user):
    if field.blank:
        return ''
    return 'http://{}.anon.example.com'.format(instance.pk)


@register(
    models.UUIDField,
)
def anonymise_uuid(instance, field_name, field, value, user):
    if field.null:
        return None

    if field.unique:
        return uuid.uuid4()

    return uuid.UUID('{00000000-0000-0000-0000-000000000000}')


@register(
    models.ForeignKey,
    models.OneToOneField,
)
def anonymise_relationship(instance, field_name, field, value, user):
    if field.null:
        return None

    raise AnonymiseError(
        'Cannot anonymise {} - can only null relationship field. Put into fk_fields to do this.'.format(
            field_name,
        )
    )


@register(
    models.ManyToManyField,
)
def anonymise_manytomany(instance, field_name, field, value, user):
    raise AnonymiseError(
        'Cannot anonymise {} - cannot anonymise ManyToManyField. Put into set_fields to do this.'.format(
            field_name,
        )
    )


def anonymise_field(instance, field_name, user):
    """
    Default field anonymiser
    """
    cls = instance.__class__

    # Check field isn't pk
    if cls._meta.pk.name == field_name:
        raise AnonymiseError('Cannot anonymise primary key')

    privacy_meta = getattr(instance, GDPR_PRIVACY_INSTANCE_NAME)

    if field_name in privacy_meta.fk_fields:
        field = getattr(instance, field_name)

        if field is not None:
            instance._log_gdpr_recursive(start=True)
            field.anonymise(user=user)
            instance._log_gdpr_recursive(start=False)

    elif field_name in privacy_meta.set_fields:
        field = getattr(instance, field_name).all()
        num_items = field.count()

        if num_items > 0:
            instance._log_gdpr_recursive(start=True)

        [o.anonymise(user=user) for o in field]

        if num_items > 0:
            instance._log_gdpr_recursive(start=False)

    else:
        # Find field
        field = cls._meta.get_field(field_name)
        # Find anonymiser
        if field.__class__ not in anonymisers:
            raise AnonymiseError('Unknown field type for anonymiser')
        anonymiser = anonymisers[field.__class__]
        value = getattr(instance, field_name)

        # Anonymise
        if value is not None:
            anonymised = anonymiser(instance, field_name, field, value, user)
            setattr(instance, field_name, anonymised)


def anonymise_related_objects(obj, anonymised=None, user=None):
    """
    See if there are any related models which need to be anonymised.

    They will be any reverse relations to PrivacyModel subclasses where their
    OneToOneField and ForeignKey on_delete is ANONYMISE.
    """
    if anonymised is None:
        anonymised = []

    relation_fields = [
        field for field in type(obj)._meta.get_fields()
        if (
                (field.one_to_many or field.one_to_one) and
                field.auto_created and
                not field.concrete and
                field.related_model in registry and
                isinstance(field.on_delete, ANONYMISE)
        )
    ]

    for field in relation_fields:
        related_objects = field.related_model._base_manager.filter(
            **{str(field.field.name): obj}
        )
        for related_obj in related_objects:
            if related_obj not in anonymised:
                related_obj.anonymise()
                anonymised.append(related_obj)

    return anonymised


def get_anon_log_for(obj):
    """
    See if there are any related models which need to be anonymised.

    They will be any reverse relations to PrivacyModel subclasses where their
    OneToOneField and ForeignKey on_delete is ANONYMISE.
    """
    if not obj.anonymised:
        return "%s is not anonymised yet." % obj

    from gdpr_assist.models import EventLog
    logs = EventLog.objects.order_by('log_time')

    top_level_log_lines = EventLog.objects.for_instance(obj).values('log_time', 'event', 'app_label', 'model_name', 'target_pk', 'acting_user')

    if top_level_log_lines.count() > 0:
        actual_anon_log_line = top_level_log_lines.first()

        lines = logs.filter(log_time__gte=actual_anon_log_line["log_time"],
                            log_time__lte=top_level_log_lines.last()["log_time"]). \
            values('log_time', 'event', 'app_label', 'model_name', 'target_pk', 'acting_user')

        user = str(actual_anon_log_line["acting_user"]) if actual_anon_log_line["acting_user"] else "[Non-descript user]"

        res = "%s #%s starting to anonymise [by %s on %s].\n" % (
            actual_anon_log_line['model_name'],
            actual_anon_log_line['target_pk'],
            user,
            actual_anon_log_line["log_time"].strftime("%Y-%m-%d %H:%M:%S")
        )
        indent_level = 0

        tabify = lambda x: "\t" * x if x > 0 else ""

        for l in lines:

            if l["event"] == EventLog.EVENT_RECURSIVE_START:
                res += "%sStarting recursive for %s #%s.\n" % (tabify(indent_level), l['model_name'], l['target_pk'])
                indent_level += 1

            elif l["event"] == EventLog.EVENT_RECURSIVE_END:
                indent_level -= 1
                res += "%sEnding recursive for %s #%s.\n" % (tabify(indent_level), l['model_name'], l['target_pk'])
            else:
                res += "%s%s #%s flat fields anonymised.\n" % (tabify(indent_level), l['model_name'], l['target_pk'])

        print(res)
        return res
    else:
        return "%s is anonymised, but does not have matching logs." % obj
