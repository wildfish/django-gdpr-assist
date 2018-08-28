"""
Test privacy event logging
"""
import six

from django.test import TestCase

from model_mommy import mommy

from gdpr_assist.models import EventLog

from .gdpr_assist_tests_app.models import (
    ModelWithPrivacyMeta,
    ModelWithoutPrivacyMeta,
)


class TestLogger(TestCase):
    def setUp(self):
        EventLog.objects.all().delete()

    def test_delete_privacy_object__deletion_logged(self):
        obj = mommy.make(ModelWithPrivacyMeta)
        self.assertEqual(EventLog.objects.count(), 0)
        obj_pk = obj.pk

        obj.delete()
        self.assertEqual(EventLog.objects.count(), 1)

        log = EventLog.objects.first()
        self.assertEqual(log.event, EventLog.EVENT_DELETE)
        self.assertEqual(log.app_label, 'gdpr_assist_tests_app')
        self.assertEqual(log.model_name, 'ModelWithPrivacyMeta')
        self.assertEqual(log.target_pk, six.text_type(obj_pk))

    def test_anonymise_privacy_object__anonymisation_logged(self):
        obj = mommy.make(ModelWithPrivacyMeta)
        self.assertEqual(EventLog.objects.count(), 0)

        obj.anonymise()
        self.assertEqual(EventLog.objects.count(), 1)

        log = EventLog.objects.first()
        self.assertEqual(log.event, EventLog.EVENT_ANONYMISE)
        self.assertEqual(log.app_label, 'gdpr_assist_tests_app')
        self.assertEqual(log.model_name, 'ModelWithPrivacyMeta')
        self.assertEqual(log.target_pk, six.text_type(obj.pk))

    def test_delete_normal_object__deletion_not_logged(self):
        obj = mommy.make(ModelWithoutPrivacyMeta)
        self.assertEqual(EventLog.objects.count(), 0)

        obj.delete()
        self.assertEqual(EventLog.objects.count(), 0)

    def test_logged_object_get_target__finds_correct_object(self):
        obj = mommy.make(ModelWithPrivacyMeta)
        self.assertEqual(EventLog.objects.count(), 0)

        obj.anonymise()
        self.assertEqual(EventLog.objects.count(), 1)

        log = EventLog.objects.first()
        found = log.get_target()
        self.assertEqual(obj.pk, found.pk)
        self.assertEqual(obj.chars, found.chars)
        self.assertEqual(obj.email, found.email)

    def test_logged_object_deleted_get_target__returns_none(self):
        obj = mommy.make(ModelWithPrivacyMeta)
        self.assertEqual(EventLog.objects.count(), 0)

        obj.delete()
        self.assertEqual(EventLog.objects.count(), 1)

        log = EventLog.objects.first()
        found = log.get_target()
        self.assertIsNone(found)
