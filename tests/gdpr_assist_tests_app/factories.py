import factory
from django.core.files.base import ContentFile
from django.db import models
from factory.django import DjangoModelFactory

from .models import (
    forbidden_models,
    not_nullable_models,
    nullable_models,
)


@factory.use_strategy(factory.BUILD_STRATEGY)
class TestModelForKnownCustomFieldFactory(DjangoModelFactory):
    class Meta:
        model = "gdpr_assist_tests_app.TestModelForKnownCustomField"


@factory.use_strategy(factory.BUILD_STRATEGY)
class PrivateTargetModelFactory(DjangoModelFactory):
    class Meta:
        model = "gdpr_assist_tests_app.PrivateTargetModel"


@factory.use_strategy(factory.BUILD_STRATEGY)
class PrivateUnregisteredTargetModelFactory(DjangoModelFactory):
    class Meta:
        model = "gdpr_assist_tests_app.PrivateUnregisteredTargetModel"


@factory.use_strategy(factory.BUILD_STRATEGY)
class OneToOneFieldModelFactory(DjangoModelFactory):
    class Meta:
        model = "gdpr_assist_tests_app.OneToOneFieldModel"


@factory.use_strategy(factory.BUILD_STRATEGY)
class ForeignKeyModelFactory(DjangoModelFactory):
    class Meta:
        model = "gdpr_assist_tests_app.ForeignKeyModel"


@factory.use_strategy(factory.BUILD_STRATEGY)
class ForeignKeyToUnregisteredModelFactory(DjangoModelFactory):
    class Meta:
        model = "gdpr_assist_tests_app.ForeignKeyToUnregisteredModel"


@factory.use_strategy(factory.BUILD_STRATEGY)
class TargetModelFactory(DjangoModelFactory):
    class Meta:
        model = "gdpr_assist_tests_app.TargetModel"


@factory.use_strategy(factory.BUILD_STRATEGY)
class ModelWithPrivacyMetaFactory(DjangoModelFactory):
    class Meta:
        model = "gdpr_assist_tests_app.ModelWithPrivacyMeta"


@factory.use_strategy(factory.BUILD_STRATEGY)
class ModelWithoutPrivacyMetaFactory(DjangoModelFactory):
    class Meta:
        model = "gdpr_assist_tests_app.ModelWithoutPrivacyMeta"


@factory.use_strategy(factory.BUILD_STRATEGY)
class FirstSearchModelFactory(DjangoModelFactory):
    class Meta:
        model = "gdpr_assist_tests_app.FirstSearchModel"


@factory.use_strategy(factory.BUILD_STRATEGY)
class SecondSearchModelFactory(DjangoModelFactory):
    class Meta:
        model = "gdpr_assist_tests_app.SecondSearchModel"


@factory.use_strategy(factory.BUILD_STRATEGY)
class ThirdSearchModelFactory(DjangoModelFactory):
    class Meta:
        model = "gdpr_assist_tests_app.ThirdSearchModel"


def field_factory_factory(field_class, factory_name, model):
    Meta = type("Meta", (object,), {"model": model, })

    attributes = {
        "Meta": Meta,
    }

    for field, definition in factories_field_definition.get(field_class, {}).items():
        attributes[field] = definition

    Factory = type(
        str(factory_name.format(
            field_class.__name__ if hasattr(field_class, "__name__") else field_class
        )),
        (DjangoModelFactory,),
        attributes,
    )

    return factory.use_strategy(factory.BUILD_STRATEGY)(Factory)


factories_field_definition = {
    models.ImageField: {
        "field": factory.LazyAttribute(
            lambda _: ContentFile(
                factory.django.ImageField()._make_data(
                    {'width': 1024, 'height': 768}
                ), 'example.jpg'
            )
        ),
    },
    models.FileField: {
        "field": factory.django.FileField(filename='the_file.dat')
    },
    models.OneToOneField: {
        "field": factory.SubFactory(TargetModelFactory),
    },
    models.ForeignKey: {
        "field": factory.SubFactory(TargetModelFactory),
    },
}


not_nullable_factories = {
    field_class: field_factory_factory(field_class, "TestModelFor{}Factory", model)
    for field_class, model in not_nullable_models.items()
}

nullable_factories = {
    field_class: field_factory_factory(field_class, "TestModelFor{}Factory", model)
    for field_class, model in nullable_models.items()
}

forbidden_factories = {
    field_class: field_factory_factory(field_class, "TestModelFor{}Factory", model)
    for field_class, model in forbidden_models.items()
}
