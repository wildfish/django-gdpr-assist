"""
Test model and queryset anonymisation
"""
import datetime
from decimal import Decimal
from freezegun import freeze_time
import os
import six
import uuid

from django.db import models
from django.test import TestCase

from model_mommy import mommy

import gdpr_assist

from .gdpr_assist_tests_app.models import (
    not_nullable_models,
    nullable_models,
    forbidden_models,
    UnknownCustomField,
    TestModelForKnownCustomField,
    PrivateTargetModel,
    PrivateUnregisteredTargetModel,
    OneToOneFieldModel,
    ForeignKeyModel,
    ForeignKeyToUnregisteredModel,
)
from .base import MigrationTestCase


class TestAnonymisationBase(TestCase):
    def get_model(self, key):
        return self.models[key]

    def create(self, key, value):
        obj = self.get_model(key).objects.create(field=value)
        return obj

    def clean_file_field(self, field):
        if os.path.isfile(field.path):
            os.remove(field.path)


class TestOnDeleteAnonymise(TestCase):
    def test_anonymise_action__set_null__initialises(self):
        action = gdpr_assist.ANONYMISE(models.SET_NULL)
        self.assertIsInstance(action, gdpr_assist.ANONYMISE)

    def test_anonymise_action__set_default__initialises(self):
        action = gdpr_assist.ANONYMISE(models.SET_DEFAULT)
        self.assertIsInstance(action, gdpr_assist.ANONYMISE)

    def test_anonymise_action__cascade__raises_error(self):
        with self.assertRaises(ValueError) as cm:
            gdpr_assist.ANONYMISE(models.CASCADE)
        self.assertEqual('Cannot ANONYMISE(CASCADE)', str(cm.exception))

    def test_anonymise_action__protect__raises_error(self):
        with self.assertRaises(ValueError) as cm:
            gdpr_assist.ANONYMISE(models.PROTECT)
        self.assertEqual('Cannot ANONYMISE(PROTECT)', str(cm.exception))


class TestOnDeleteAnonymiseDeconstruct(MigrationTestCase):
    """
    Test on_delete=ANONYMISE can be deconstructed
    """
    def test_anonymise_deconstruct__deconstructs(self):
        string, imports = self.serialize(
            gdpr_assist.ANONYMISE(models.SET_NULL),
        )
        self.assertEqual(
            string,
            'gdpr_assist.ANONYMISE(django.db.models.deletion.SET_NULL)',
        )
        self.serialize_round_trip(
            gdpr_assist.ANONYMISE(models.SET_NULL),
        )


class TestNotNullableAnonymisation(TestAnonymisationBase):
    """
    Test all field types when they do not have null=True
    """
    models = not_nullable_models

    def test_big_integer__anonymise_to_zero(self):
        value = 1
        obj = self.create(models.BigIntegerField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertEqual(obj.field, 0)

    def test_integer__anonymise_to_zero(self):
        value = 1
        obj = self.create(models.IntegerField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertEqual(obj.field, 0)

    def test_positive_integer__anonymise_to_zero(self):
        value = 1
        obj = self.create(models.PositiveIntegerField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertEqual(obj.field, 0)

    def test_positive_small_integer__anonymise_to_zero(self):
        value = 1
        obj = self.create(models.PositiveSmallIntegerField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertEqual(obj.field, 0)

    def test_small_integer__anonymise_to_zero(self):
        value = 1
        obj = self.create(models.SmallIntegerField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertEqual(obj.field, 0)

    def test_charfield__anonymise_to_pk(self):
        value = 'test'
        obj = self.create(models.CharField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertEqual(obj.field, str(obj.pk))

    def test_slugfield__anonymise_to_pk(self):
        value = 'test'
        obj = self.create(models.SlugField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertEqual(obj.field, str(obj.pk))

    def test_textfield__anonymise_to_pk(self):
        value = 'test'
        obj = self.create(models.TextField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertEqual(obj.field, str(obj.pk))

    def test_binaryfield__anonymise_to_false(self):
        value = b'value'
        obj = self.create(models.BinaryField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertEqual(obj.field, b'')

    def test_booleanfield__anonymise_to_false(self):
        value = True
        obj = self.create(models.BooleanField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertEqual(obj.field, False)

    def test_nullbooleanfield__anonymise_to_none(self):
        # Trick question, NullBooleanField is always nullable
        value = True
        obj = self.create(models.NullBooleanField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertEqual(obj.field, None)

    @freeze_time('2001-01-01 12:00:00')
    def test_datefield__anonymise_to_now(self):
        value = datetime.date.today() + datetime.timedelta(days=1)
        obj = self.create(models.DateField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertEqual(obj.field, datetime.date.today())

    @freeze_time('2001-01-01 12:00:00')
    def test_datetimefield__anonymise_to_now(self):
        value = datetime.datetime.now() + datetime.timedelta(days=1)
        obj = self.create(models.DateTimeField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertEqual(obj.field, datetime.datetime.now())

    def test_timefield__anonymise_to_zero(self):
        value = datetime.time(12, 0)
        obj = self.create(models.TimeField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertEqual(obj.field, datetime.time())

    def test_durationfield__anonymise_to_zero(self):
        value = datetime.timedelta(days=1)
        obj = self.create(models.DurationField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertEqual(obj.field, datetime.timedelta(0))

    def test_decimalfield__anonymise_to_zero(self):
        value = Decimal(1.1)
        obj = self.create(models.DecimalField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertEqual(obj.field, Decimal(0))

    def test_floatfield__anonymise_to_zero(self):
        value = 1.1
        obj = self.create(models.FloatField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertEqual(obj.field, 0)

    def test_filefield__raise_exception(self):
        obj = mommy.make(
            self.get_model(models.FileField),
            _fill_optional=True,
            _create_files=True,
            anonymised=False,
        )
        self.assertFalse(obj.anonymised)
        orig = obj.field

        with self.assertRaises(gdpr_assist.AnonymiseError) as cm:
            obj.anonymise()
        self.assertEqual(
            'Cannot anonymise field - can only null file fields',
            str(cm.exception),
        )
        self.clean_file_field(orig)

    def test_filepathfield__raise_exception(self):
        value = '/tmp'
        obj = self.create(models.FilePathField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        with self.assertRaises(gdpr_assist.AnonymiseError) as cm:
            obj.anonymise()
        self.assertEqual(
            'Cannot anonymise field - can only null file fields',
            str(cm.exception),
        )

    def test_imagefield__raise_exception(self):
        obj = mommy.make(
            self.get_model(models.ImageField),
            _fill_optional=True,
            _create_files=True,
            anonymised=False,
        )
        self.assertFalse(obj.anonymised)
        orig = obj.field

        with self.assertRaises(gdpr_assist.AnonymiseError) as cm:
            obj.anonymise()
        self.assertEqual(
            'Cannot anonymise field - can only null file fields',
            str(cm.exception),
        )
        self.clean_file_field(orig)

    def test_emailfield__anonymise_to_anon(self):
        value = 'test@example.com'
        obj = self.create(models.EmailField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertEqual(obj.field, '{}@anon.example.com'.format(obj.pk))

    def test_genericipaddressfield__anonymise_to_zero(self):
        value = '127.0.0.1'
        obj = self.create(models.GenericIPAddressField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertEqual(obj.field, '0.0.0.0')

    def test_urlfield__anonymise_to_anon(self):
        value = 'http://example.com'
        obj = self.create(models.URLField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertEqual(
            obj.field,
            'http://{}.anon.example.com'.format(obj.pk),
        )

    def test_uuidfield__anonymise_to_zero(self):
        value = uuid.uuid4()
        obj = self.create(models.UUIDField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertNotEqual(obj.field, value)
        self.assertEqual(
            obj.field,
            uuid.UUID('{00000000-0000-0000-0000-000000000000}'),
        )

    def test_uuidfield_unique__anonymise_to_random(self):
        value = uuid.uuid4()
        obj = self.create('UUIDField-unique', value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertNotEqual(obj.field, value)
        self.assertNotEqual(
            obj.field,
            uuid.UUID('{00000000-0000-0000-0000-000000000000}'),
        )
        six.assertRegex(
            self,
            str(obj.field),
            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
        )

    def test_foreignkey__raise_exception(self):
        obj = mommy.make(
            self.get_model(models.ForeignKey),
            _fill_optional=True,
            _create_files=True,
            anonymised=False,
        )
        self.assertFalse(obj.anonymised)

        with self.assertRaises(gdpr_assist.AnonymiseError) as cm:
            obj.anonymise()
        self.assertEqual(
            'Cannot anonymise field - can only null relationship field',
            str(cm.exception),
        )

    def test_onetoonefield__raise_exception(self):
        obj = mommy.make(
            self.get_model(models.OneToOneField),
            _fill_optional=True,
            _create_files=True,
            anonymised=False,
        )
        self.assertFalse(obj.anonymised)

        with self.assertRaises(gdpr_assist.AnonymiseError) as cm:
            obj.anonymise()
        self.assertEqual(
            'Cannot anonymise field - can only null relationship field',
            str(cm.exception),
        )

    def test_knowncustomfield__custom_handler_called(self):
        obj = TestModelForKnownCustomField.objects.create(field='Test')
        self.assertFalse(obj.anonymised)
        self.assertEqual(obj.field, 'Test')

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertEqual(obj.field, 'Anonymised')


class TestNullableAnonymisation(TestAnonymisationBase):
    """
    Test all field types when they do have null=True
    """

    models = nullable_models

    def test_big_integer__anonymise_to_none(self):
        value = 1
        obj = self.create(models.BigIntegerField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertIsNone(obj.field)

    def test_integer__anonymise_to_none(self):
        value = 1
        obj = self.create(models.IntegerField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertIsNone(obj.field)

    def test_positive_integer__anonymise_to_none(self):
        value = 1
        obj = self.create(models.PositiveIntegerField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertIsNone(obj.field)

    def test_positive_small_integer__anonymise_to_none(self):
        value = 1
        obj = self.create(models.PositiveSmallIntegerField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertIsNone(obj.field)

    def test_small_integer__anonymise_to_none(self):
        value = 1
        obj = self.create(models.SmallIntegerField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertIsNone(obj.field)

    def test_charfield__anonymise_to_none(self):
        value = 'test'
        obj = self.create(models.CharField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertEqual(obj.field, '')

    def test_slugfield__anonymise_to_none(self):
        value = 'test'
        obj = self.create(models.SlugField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertEqual(obj.field, '')

    def test_textfield__anonymise_to_none(self):
        value = 'test'
        obj = self.create(models.TextField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertEqual(obj.field, '')

    def test_binaryfield__anonymise_to_none(self):
        value = b'value'
        obj = self.create(models.BinaryField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertIsNone(obj.field)

    def test_nullbooleanfield__anonymise_to_none(self):
        # Trick question, NullBooleanField is always nullable
        value = True
        obj = self.create(models.NullBooleanField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertIsNone(obj.field)

    @freeze_time('2001-01-01 12:00:00')
    def test_datefield__anonymise_to_none(self):
        value = datetime.date.today()
        obj = self.create(models.DateField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertIsNone(obj.field)

    @freeze_time('2001-01-01 12:00:00')
    def test_datetimefield__anonymise_to_none(self):
        value = datetime.datetime.now()
        obj = self.create(models.DateTimeField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertIsNone(obj.field)

    def test_timefield__anonymise_to_none(self):
        value = datetime.time(12, 0)
        obj = self.create(models.TimeField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertIsNone(obj.field)

    def test_durationfield__anonymise_to_none(self):
        value = datetime.timedelta(days=1)
        obj = self.create(models.DurationField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertIsNone(obj.field)

    def test_decimalfield__anonymise_to_none(self):
        value = Decimal(1.1)
        obj = self.create(models.DecimalField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertIsNone(obj.field)

    def test_floatfield__anonymise_to_none(self):
        value = 1.1
        obj = self.create(models.FloatField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertIsNone(obj.field)

    def test_filefield__anonymise_to_none(self):
        obj = mommy.make(
            self.get_model(models.FileField),
            _fill_optional=True,
            _create_files=True,
            anonymised=False,
        )
        self.assertFalse(obj.anonymised)
        orig = obj.field

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertIsNone(obj.field._file)
        self.assertIsNone(obj.field.name)
        self.clean_file_field(orig)

    def test_filepathfield__anonymise_to_none(self):
        value = '/tmp'
        obj = self.create(models.FilePathField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertIsNone(obj.field)

    def test_imagefield__anonymise_to_none(self):
        obj = mommy.make(
            self.get_model(models.ImageField),
            _fill_optional=True,
            _create_files=True,
            anonymised=False,
        )
        self.assertFalse(obj.anonymised)
        orig = obj.field

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertIsNone(obj.field._file)
        self.assertIsNone(obj.field.name)
        self.clean_file_field(orig)

    def test_emailfield__anonymise_to_none(self):
        value = 'test@example.com'
        obj = self.create(models.EmailField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertIsNone(obj.field)

    def test_genericipaddressfield__anonymise_to_none(self):
        value = '127.0.0.1'
        obj = self.create(models.GenericIPAddressField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertIsNone(obj.field)

    def test_urlfield__anonymise_to_none(self):
        value = 'http://example.com'
        obj = self.create(models.URLField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertEqual(obj.field, '')

    def test_uuidfield__anonymise_to_none(self):
        value = uuid.uuid4()
        obj = self.create(models.UUIDField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertIsNone(obj.field)

    def test_foreignkey__anonymise_to_none(self):
        obj = mommy.make(
            self.get_model(models.ForeignKey),
            _fill_optional=True,
            _create_files=True,
            anonymised=False,
        )
        self.assertFalse(obj.anonymised)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertIsNone(obj.field)

    def test_onetoonefield__anonymise_to_none(self):
        obj = mommy.make(
            self.get_model(models.OneToOneField),
            _fill_optional=True,
            _create_files=True,
            anonymised=False,
        )
        self.assertFalse(obj.anonymised)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertIsNone(obj.field)


class TestForbiddenAnonymisation(TestAnonymisationBase):
    """
    Test field types which are forbidden
    """
    models = forbidden_models

    def test_autofield__raise_exception(self):
        obj = self.get_model(models.AutoField).objects.create()
        self.assertFalse(obj.anonymised)

        with self.assertRaises(gdpr_assist.AnonymiseError) as cm:
            obj.anonymise()
        self.assertEqual(
            'Cannot anonymise primary key',
            str(cm.exception),
        )

    def test_manytomanyfield__raise_exception(self):
        obj = mommy.make(
            self.get_model(models.ManyToManyField),
            _fill_optional=True,
            _create_files=True,
            anonymised=False,
        )
        self.assertFalse(obj.anonymised)

        with self.assertRaises(gdpr_assist.AnonymiseError) as cm:
            obj.anonymise()
        self.assertEqual(
            'Cannot anonymise field - cannot anonymise ManyToManyField',
            str(cm.exception),
        )

    def test_customfield__raise_exception(self):
        obj = self.create(UnknownCustomField, 'Test')
        self.assertFalse(obj.anonymised)

        with self.assertRaises(gdpr_assist.AnonymiseError) as cm:
            obj.anonymise()
        self.assertEqual(
            'Unknown field type for anonymiser',
            str(cm.exception),
        )


class TestRelation(TestCase):
    def test_onetoonefield_anonymise__anonymise_not_propagated(self):
        target = PrivateTargetModel.objects.create(chars='Test')
        obj = OneToOneFieldModel.objects.create(chars='Test', target=target)

        target.anonymise()
        self.assertTrue(target.anonymised)
        self.assertEqual(target.chars, '')

        obj.refresh_from_db()
        self.assertFalse(obj.anonymised)
        self.assertEqual(obj.chars, 'Test')

    def test_foreignkey_anonymise__anonymise_not_propagated(self):
        target = PrivateTargetModel.objects.create(chars='Test')
        obj = ForeignKeyModel.objects.create(chars='Test', target=target)

        target.anonymise()
        self.assertTrue(target.anonymised)
        self.assertEqual(target.chars, '')

        obj.refresh_from_db()
        self.assertFalse(obj.anonymised)
        self.assertEqual(obj.chars, 'Test')

    def test_onetoonefield_delete__anonymise_propagated(self):
        target = PrivateTargetModel.objects.create(chars='Test')
        obj = OneToOneFieldModel.objects.create(chars='Test', target=target)

        target.delete()
        obj.refresh_from_db()
        self.assertTrue(obj.anonymised)
        self.assertEqual(obj.chars, '')

    def test_foreignkey_delete__anonymise_propagated(self):
        target = PrivateTargetModel.objects.create(chars='Test')
        obj = ForeignKeyModel.objects.create(chars='Test', target=target)

        target.delete()
        obj.refresh_from_db()
        self.assertTrue(obj.anonymised)
        self.assertEqual(obj.chars, '')

    def test_foreignkey_unregistered_target_delete__anonymise_propagated(self):
        target = PrivateUnregisteredTargetModel.objects.create(chars='Test')
        obj = ForeignKeyToUnregisteredModel.objects.create(
            chars='Test',
            target=target,
        )

        target.delete()
        obj.refresh_from_db()
        self.assertTrue(obj.anonymised)
        self.assertEqual(obj.chars, '')


class TestOtherAnonymisation(TestAnonymisationBase):
    """
    Tests which don't fall under other categories
    """
    models = nullable_models

    def test_anonymise_twice_no_force__not_anonymised_twice(self):
        value = 'test'
        obj = self.create(models.CharField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertEqual(obj.field, '')
        obj.field = 'twice'

        self.assertTrue(obj.anonymised)
        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertEqual(obj.field, 'twice')

    def test_anonymise_twice_with_force__anonymised_twice(self):
        value = 'test'
        obj = self.create(models.CharField, value)
        self.assertFalse(obj.anonymised)
        orig = obj.field
        self.assertEqual(orig, value)

        obj.anonymise()
        self.assertTrue(obj.anonymised)
        self.assertEqual(obj.field, '')
        obj.field = 'twice'

        obj.anonymise(force=True)
        self.assertTrue(obj.anonymised)
        self.assertEqual(obj.field, '')


class TestQuerySet(TestCase):
    def test_queryset_anonymise__anonymise_all(self):
        objs = []
        for i in range(5):
            objs.append(
                PrivateTargetModel.objects.create(chars='Test {}'.format(i))
            )

        qs = PrivateTargetModel.objects.filter(
            pk__in=[obj.pk for obj in objs],
        )

        qs.anonymise()
        for i in range(5):
            objs[i].refresh_from_db()
            self.assertEqual(objs[i].chars, '')

    def test_queryset_anonymise__anonymise_not_propagated(self):
        targets = []
        for i in range(5):
            targets.append(
                PrivateTargetModel.objects.create(chars='Test {}'.format(i))
            )

        objs = []
        for i in range(5):
            objs.append(
                OneToOneFieldModel.objects.create(
                    chars='Test {}'.format(i),
                    target=targets[i],
                )
            )

        qs = PrivateTargetModel.objects.filter(
            pk__in=[target.pk for target in targets],
        )

        qs.anonymise()
        for i in range(5):
            targets[i].refresh_from_db()
            self.assertEqual(targets[i].chars, '')

            objs[i].refresh_from_db()
            self.assertEqual(objs[i].chars, 'Test {}'.format(i))

    def test_queryset_delete__anonymise_propagated(self):
        targets = []
        for i in range(5):
            targets.append(
                PrivateTargetModel.objects.create(chars='Test {}'.format(i))
            )

        objs = []
        for i in range(5):
            objs.append(
                OneToOneFieldModel.objects.create(
                    chars='Test {}'.format(i),
                    target=targets[i],
                )
            )

        qs = PrivateTargetModel.objects.filter(
            pk__in=[target.pk for target in targets],
        )

        qs.delete()
        for i in range(5):
            objs[i].refresh_from_db()
            self.assertEqual(objs[i].chars, '')
