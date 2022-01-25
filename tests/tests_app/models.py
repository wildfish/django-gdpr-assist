"""
Test models
"""
from __future__ import unicode_literals

import uuid

import django
from django.db import models

import gdpr_assist


class ModelWithPrivacyMeta(models.Model):
    """
    Test PrivacyMeta definition on the model
    """

    chars = models.CharField(max_length=255)
    email = models.EmailField()

    class PrivacyMeta:
        fields = ["chars", "email"]


class ModelWithoutPrivacyMeta(models.Model):
    """
    Test no PrivacyMeta definition
    """

    chars = models.CharField(max_length=255)
    email = models.EmailField()


class ModelWithPrivacyMetaCanNotAnonymise(models.Model):
    """
    Test PrivacyMeta definition on the model
    """

    chars = models.CharField(max_length=255)
    email = models.EmailField()

    class PrivacyMeta:
        fields = ["chars", "email"]
        can_anonymise = False


class InheritedModelWithPrivacyMeta(ModelWithPrivacyMeta):
    class PrivacyMeta:
        fields = ["chars"]


class InheritedModelWithoutPrivacyMeta(ModelWithoutPrivacyMeta):
    title = models.CharField(max_length=255)



class TargetModel(models.Model):
    """
    Target model for tests, no private data
    """

    chars = models.CharField(max_length=255, blank=True)


class PrivateTargetModel(models.Model):
    """
    Target model for tests with private data
    """

    chars = models.CharField(max_length=255, blank=True)

    class PrivacyMeta:
        fields = ["chars"]


class PrivateUnregisteredTargetModel(models.Model):
    """
    Target model which isn't registered with gdpr-assist
    """

    chars = models.CharField(max_length=255, blank=True)


class PrivateTargetCanNotAnonymiseModel(models.Model):
    """
    Target model which is register but anonymisation is disabled.
    """

    chars = models.CharField(max_length=255, blank=True)

    class PrivacyMeta:
        fields = ["chars"]


def field_model_factory(model_name, field_instance, field_name="field"):
    cls = type(
        str(model_name.format(field_instance.__class__.__name__)),
        (models.Model,),
        {"__module__": TargetModel.__module__, field_name: field_instance},
    )

    class PrivacyMeta:
        fields = [field_name]

    gdpr_assist.register(cls, PrivacyMeta)
    return cls


# Test all fields that gdpr-assist can blank without nulling
fields = [
    models.BigIntegerField(),
    models.IntegerField(),
    models.PositiveIntegerField(),
    models.PositiveSmallIntegerField(),
    models.SmallIntegerField(),
    models.CharField(max_length=255),
    models.SlugField(),
    models.TextField(),
    models.BinaryField(),
    models.BooleanField(),
    models.DateField(),
    models.DateTimeField(),
    models.DurationField(),
    models.TimeField(),
    models.DecimalField(decimal_places=2, max_digits=7),
    models.FloatField(),
    models.FileField(),
    models.FilePathField(),
    models.ImageField(),
    models.EmailField(),
    models.GenericIPAddressField(),
    models.URLField(),
    models.UUIDField(),
    models.ForeignKey(TargetModel, on_delete=models.CASCADE, related_name="+"),
    models.OneToOneField(TargetModel, on_delete=models.CASCADE, related_name="+"),
]

if django.VERSION < (4, 0):  # NullBooleanField deprecated @ 4.0
    fields.append(models.NullBooleanField())

not_nullable_models = {
    field.__class__: field_model_factory("TestModelFor{}", field)
    for field in fields
}

not_nullable_models.update(
    {
        "UUIDField-unique": field_model_factory(
            "TestModelFor{}Unique", models.UUIDField(unique=True)
        )
    }
)


# Test all fields that can be nulled
#
# Excludes BooleanField - can never be null
nullable_fields = [
    models.BigIntegerField(blank=True, null=True),
    models.IntegerField(blank=True, null=True),
    models.PositiveIntegerField(blank=True, null=True),
    models.PositiveSmallIntegerField(blank=True, null=True),
    models.SmallIntegerField(blank=True, null=True),
    models.CharField(max_length=255, blank=True),
    models.SlugField(blank=True),
    models.TextField(blank=True),
    models.BinaryField(blank=True, null=True),
    models.DateField(blank=True, null=True),
    models.DateTimeField(blank=True, null=True),
    models.DurationField(blank=True, null=True),
    models.TimeField(blank=True, null=True),
    models.DecimalField(decimal_places=2, max_digits=7, blank=True, null=True),
    models.FloatField(blank=True, null=True),
    models.FileField(blank=True, null=True),
    models.FilePathField(blank=True, null=True),
    models.ImageField(blank=True, null=True),
    models.EmailField(blank=True, null=True),
    models.GenericIPAddressField(blank=True, null=True),
    models.URLField(blank=True, null=True),
    models.UUIDField(blank=True, null=True),
    models.ForeignKey(
        TargetModel,
        blank=True,
        null=True,
        related_name="+",
        on_delete=models.CASCADE,
    ),
    models.OneToOneField(
        TargetModel,
        blank=True,
        null=True,
        related_name="+",
        on_delete=models.CASCADE,
    ),
]


if django.VERSION < (4, 0):  # NullBooleanField deprecated @ 4.0
    nullable_fields.append(models.NullBooleanField())


if django.VERSION > (3, 0):  # Nullable BooleanField added @ 3.1
    nullable_fields.append(models.BooleanField(blank=True, null=True))


nullable_models = {
    field.__class__: field_model_factory("TestModelForNullable{}", field)
    for field in nullable_fields
}


class UnknownCustomField(models.CharField):
    pass


forbidden_models = {
    models.AutoField: field_model_factory(
        model_name="TestModelForbiddenForAutoField",
        field_instance=models.AutoField(primary_key=True),
        field_name="id",
    ),
    models.ManyToManyField: field_model_factory(
        model_name="TestModelForbiddenForManyToManyField",
        field_instance=models.ManyToManyField(TargetModel, related_name="+"),
    ),
    UnknownCustomField: field_model_factory(
        model_name="TestModelForbiddenForUnknownCustomField",
        field_instance=UnknownCustomField(max_length=255),
    ),
}


class KnownCustomField(models.CharField):
    pass


class TestModelForKnownCustomField(models.Model):
    field = KnownCustomField(max_length=255)

    class PrivacyMeta:
        def anonymise_field(self, instance):
            instance.field = "Anonymised"


# Test relations


class OneToOneFieldModel(models.Model):
    chars = models.CharField(max_length=255, blank=True)
    target = models.OneToOneField(
        "PrivateTargetModel",
        null=True,
        blank=True,
        on_delete=gdpr_assist.ANONYMISE(models.SET_NULL),
        related_name="onetoonefield",
    )

    class PrivacyMeta:
        fields = ["chars"]


class ForeignKeyModel(models.Model):
    chars = models.CharField(max_length=255, blank=True)
    target = models.ForeignKey(
        "PrivateTargetModel",
        null=True,
        blank=True,
        on_delete=gdpr_assist.ANONYMISE(models.SET_NULL),
        related_name="foreignkey",
    )

    class PrivacyMeta:
        fields = ["chars"]


class ForeignKeyToUnregisteredModel(models.Model):
    chars = models.CharField(max_length=255, blank=True)
    target = models.ForeignKey(
        "PrivateUnregisteredTargetModel",
        null=True,
        blank=True,
        on_delete=gdpr_assist.ANONYMISE(models.SET_NULL),
        related_name="foreignkey",
    )

    class PrivacyMeta:
        fields = ["chars"]


class ForeignKeyToCanNotAnonymisedModel(models.Model):
    chars = models.CharField(max_length=255, blank=True)
    target = models.ForeignKey(
        "PrivateTargetCanNotAnonymiseModel",
        null=True,
        blank=True,
        on_delete=gdpr_assist.ANONYMISE(models.SET_NULL),
        related_name="foreignkey",
    )

    class PrivacyMeta:
        fields = ["chars"]
        can_anonymise = False


class FirstSearchModel(models.Model):
    """
    Test PrivacyMeta search and export
    """

    chars = models.CharField(max_length=255)
    email = models.EmailField()

    class PrivacyMeta:
        fields = ["chars", "email"]
        search_fields = ["email"]
        export_fields = ["email"]


class SecondSearchModel(models.Model):
    """
    Test PrivacyMeta search and export
    """

    chars = models.CharField(max_length=255)
    email = models.EmailField()

    class PrivacyMeta:
        fields = ["chars", "email"]
        search_fields = ["email"]
        export_filename = "second_search.csv"


class ThirdSearchModel(models.Model):
    """
    Test PrivacyMeta search and export
    """

    chars = models.CharField(max_length=255)
    email = models.EmailField()

    class PrivacyMeta:
        fields = ["chars", "email"]
        search_fields = ["email"]
        export_exclude = ["email"]


class ForthSearchModel(models.Model):
    """
    Test PrivacyMeta search and export
    """

    chars = models.CharField(max_length=255)
    email = models.EmailField()

    class PrivacyMeta:
        fields = ["chars", "email"]
        search_fields = ["email"]
        export_exclude = ["email"]
        can_anonymise = False


class UUIDasPK(models.Model):
    """
    Test PrivacyMeta definition on the model with non-standard pk
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chars = models.CharField(max_length=255)

    class PrivacyMeta:
        fields = ["chars"]


class UUIDasPKSmallField(models.Model):
    """
    Test PrivacyMeta definition on the model with non-standard pk, where the field to be anoonymised
    is smaller then a UUID (which will be used as the value).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chars = models.CharField(max_length=10)

    class PrivacyMeta:
        fields = ["chars"]
