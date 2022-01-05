"""
Test privacy event logging
"""
from django.test import TestCase, override_settings

from model_bakery import baker

from gdpr_assist.models import EventLog

from .tests_app.models import (
    ModelWithoutPrivacyMeta,
    ModelWithPrivacyMeta,
    ModelWithPrivacyMetaCanNotAnonymise,
)


class TestLogger(TestCase):
    databases = "__all__"

    def setUp(self):
        EventLog.objects.all().delete()

    def test_delete_privacy_object__deletion_logged(self):
        obj = baker.make(ModelWithPrivacyMeta)
        self.assertEqual(EventLog.objects.count(), 0)
        obj_pk = obj.pk

        obj.delete()
        self.assertEqual(EventLog.objects.count(), 1)

        log = EventLog.objects.first()
        self.assertEqual(log.event, EventLog.EVENT_DELETE)
        self.assertEqual(log.app_label, "tests_app")
        self.assertEqual(log.model_name, "ModelWithPrivacyMeta")
        self.assertEqual(log.target_pk, str(obj_pk))

    def test_anonymise_privacy_object__anonymisation_logged(self):
        obj = baker.make(ModelWithPrivacyMeta)
        self.assertEqual(EventLog.objects.count(), 0)

        obj.anonymise()
        self.assertEqual(EventLog.objects.count(), 1)

        log = EventLog.objects.first()
        self.assertEqual(log.event, EventLog.EVENT_ANONYMISE)
        self.assertEqual(log.app_label, "tests_app")
        self.assertEqual(log.model_name, "ModelWithPrivacyMeta")
        self.assertEqual(log.target_pk, str(obj.pk))

    @override_settings(GDPR_LOG_ON_ANONYMISE=False)
    def test_anonymise_privacy_object__anonymisation_not_logged(self):
        obj = baker.make(ModelWithPrivacyMeta)
        self.assertEqual(EventLog.objects.count(), 0)

        obj.anonymise()
        self.assertEqual(EventLog.objects.count(), 0)

    def test_delete_normal_object__deletion_not_logged(self):
        obj = baker.make(ModelWithoutPrivacyMeta)
        self.assertEqual(EventLog.objects.count(), 0)

        obj.delete()
        self.assertEqual(EventLog.objects.count(), 0)

    def test_logged_object_get_target__finds_correct_object(self):
        obj = baker.make(ModelWithPrivacyMeta)
        self.assertEqual(EventLog.objects.count(), 0)

        obj.anonymise()
        self.assertEqual(EventLog.objects.count(), 1)

        log = EventLog.objects.first()
        found = log.get_target()
        self.assertEqual(obj.pk, found.pk)
        self.assertEqual(obj.chars, found.chars)
        self.assertEqual(obj.email, found.email)

    def test_logged_object_deleted_get_target__returns_none(self):
        obj = baker.make(ModelWithPrivacyMeta)
        self.assertEqual(EventLog.objects.count(), 0)

        obj.delete()
        self.assertEqual(EventLog.objects.count(), 1)

        log = EventLog.objects.first()
        found = log.get_target()
        self.assertIsNone(found)

    def test_anonymise_privacy_object__disabled_anonymise__anonymisation__not__logged(
        self,
    ):
        obj = baker.make(ModelWithPrivacyMetaCanNotAnonymise)
        self.assertEqual(EventLog.objects.count(), 0)

        obj.anonymise()
        self.assertEqual(EventLog.objects.count(), 0)
