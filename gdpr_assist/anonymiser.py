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
    models.ManyToOneRel,
)
def anonymise_relationship(instance, field_name, field, value, user):
    if field.null:
        return None
    try:
        getattr(instance, field_name).anonymise()  # pass down to anonymise the related obj
    except AttributeError:
        print("Cannot call anonymise on field %s, please make its model %s a subclass of PrivacyModel" % (field_name, field.related_model.__name__))


@register(
    models.ManyToManyField,
    models.ManyToManyRel
)
def anonymise_manytomany(instance, field_name, field, value, user):
    try:
        getattr(instance, field_name).all().anonymise()  # pass down to anonymise each of the related objs
    except AttributeError:
        print("Cannot call anonymise on field %s, please make its model %s a subclass of PrivacyModel" % (field_name, field.model.__name__))


def anonymise_field(instance, field_name, user):
    """
    Default field anonymiser
    """
    cls = instance.__class__

    # Check field isn't pk
    if cls._meta.pk.name == field_name:
        raise AnonymiseError('Cannot anonymise primary key')

    # Find field
    from django.core.exceptions import FieldDoesNotExist
    try:
        field = cls._meta.get_field(field_name)
        # Find anonymiser
        if field.__class__ not in anonymisers:
            raise AnonymiseError('Unknown field type for anonymiser')
        anonymiser = anonymisers[field.__class__]
        value = getattr(instance, field_name)

    except FieldDoesNotExist:
        field = getattr(instance, field_name)  # for related fields and m2ms
        anonymiser = anonymise_manytomany
        value = None  # this is meaningless for relationship fields



    # Anonymise
    anonymised = anonymiser(instance, field_name, field, value, user)
    if anonymiser not in [anonymise_manytomany, anonymise_relationship]:
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
