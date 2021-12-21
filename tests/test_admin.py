"""
Test admin tools
"""
import csv
import zipfile
from io import BytesIO, TextIOWrapper

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import Client, TestCase

from model_bakery import baker

import gdpr_assist

from .tests_app.models import (
    FirstSearchModel,
    ForthSearchModel,
    ModelWithPrivacyMeta,
    ModelWithPrivacyMetaCanNotAnonymise,
    SecondSearchModel,
)


model_root_url = "/admin/tests_app/modelwithprivacymeta/"
tool_root_url = "/admin/gdpr_assist/personaldata/"


class AdminTestCase(TestCase):
    databases = "__all__"

    def setUp(self):
        self.client = Client()
        user = User.objects.create_superuser(
            username="test", email="test@example.com", password="test"
        )

        self.client.force_login(user)


class TestModelAdmin(AdminTestCase):
    def test_changelist__anonymise_action_present(self):
        baker.make(ModelWithPrivacyMeta)
        response = self.client.get(model_root_url)
        self.assertContains(response, '<option value="anonymise">')

    def test_anonymise_action_submit__redirect_to_anonymise_view(self):
        obj_1 = baker.make(ModelWithPrivacyMeta)
        obj_2 = baker.make(ModelWithPrivacyMeta)

        response = self.client.post(
            model_root_url,
            {"action": "anonymise", "_selected_action": [obj_1.pk, obj_2.pk]},
            follow=True,
        )

        test_url = "{root_url}anonymise/?ids={pk1},{pk2}".format(
            root_url=model_root_url, pk1=obj_1.pk, pk2=obj_2.pk
        )

        self.assertEqual(response.redirect_chain, [(test_url, 302)])
        self.assertContains(
            response,
            "<p>Are you sure you want to anonymise the following Model With Privacy Metas:</p>",
        )
        self.assertContains(
            response,
            '<input type="hidden" name="ids" value="{pk1},{pk2}">'.format(
                pk1=obj_1.pk, pk2=obj_2.pk
            ),
        )

    def test_anonymise_view_submit__redirect_to_anonymise_view(self):
        obj_1 = baker.make(ModelWithPrivacyMeta)
        obj_2 = baker.make(ModelWithPrivacyMeta)

        response = self.client.post(
            model_root_url + "anonymise/",
            {"ids": ",".join([str(obj_1.pk), str(obj_2.pk)])},
            follow=True,
        )
        obj_1.refresh_from_db()
        obj_2.refresh_from_db()
        self.assertTrue(obj_1.is_anonymised())
        self.assertTrue(obj_2.is_anonymised())

        self.assertEqual(response.redirect_chain, [(model_root_url, 302)])

        self.assertContains(
            response, '<li class="success">2 Model With Privacy Metas anonymised</li>'
        )

    def test_anonymise_view_submit__redirect_to_anonymise_view__alternate_manager(self):
        obj_1 = baker.make(User)
        obj_2 = baker.make(User)

        response = self.client.post(
            "/admin/auth/user/anonymise/",
            {"ids": ",".join([str(obj_1.pk), str(obj_2.pk)])},
            follow=True,
        )

        obj_1.refresh_from_db()
        obj_2.refresh_from_db()
        self.assertTrue(obj_1.is_anonymised())
        self.assertTrue(obj_2.is_anonymised())

        self.assertEqual(response.redirect_chain, [("/admin/auth/user/", 302)])

        self.assertContains(
            response, '<li class="success">2 Users anonymised</li>'
        )

    def test_anonymise_action_submit__can_anonymise_disabled__404(self):
        obj_1 = baker.make(ModelWithPrivacyMetaCanNotAnonymise)
        obj_2 = baker.make(ModelWithPrivacyMetaCanNotAnonymise)

        response = self.client.post(
            "/admin/tests_app/modelwithprivacymetacannotanonymise/",
            {"action": "anonymise", "_selected_action": [obj_1.pk, obj_2.pk]},
            follow=True,
        )

        self.assertEqual(response.status_code, 404)

    def test_anonymise_view_submit__can_anonymise_disabled__404(self):
        obj_1 = baker.make(ModelWithPrivacyMetaCanNotAnonymise)
        obj_2 = baker.make(ModelWithPrivacyMetaCanNotAnonymise)

        response = self.client.post(
            "/admin/tests_app/modelwithprivacymetacannotanonymise/anonymise/",
            {"ids": ",".join([str(obj_1.pk), str(obj_2.pk)])},
            follow=True,
        )

        self.assertEqual(response.status_code, 404)

        obj_1.refresh_from_db()
        obj_2.refresh_from_db()
        self.assertFalse(obj_1.is_anonymised())
        self.assertFalse(obj_2.is_anonymised())


class TestAdminTool(AdminTestCase):
    def test_tool_is_available(self):
        baker.make(FirstSearchModel)
        response = self.client.get(tool_root_url)
        self.assertContains(response, "<h1>Personal Data</h1>")

    def test_search__returns_correct_results(self):
        obj_1 = baker.make(FirstSearchModel, email="one@example.com")
        baker.make(FirstSearchModel, email="two@example.com")

        response = self.client.post(tool_root_url, {"term": "one@example.com"})
        self.assertContains(
            response, "<h2>Tests_App: First Search Model</h2>"
        )
        self.assertContains(
            response,
            '<input name="obj_pk" value="{}-{}" class="action-select" type="checkbox">'.format(
                ContentType.objects.get_for_model(FirstSearchModel).pk, obj_1.pk
            ),
        )

    def test_anonymise__records_anonymised(self):
        obj_1 = baker.make(FirstSearchModel, email="one@example.com")
        obj_2 = baker.make(FirstSearchModel, email="two@example.com")
        content_type = ContentType.objects.get_for_model(FirstSearchModel).pk

        response = self.client.post(
            tool_root_url,
            {
                "term": "one@example.com",
                "action": gdpr_assist.admin.tool.PersonalDataSearchForm.ACTION_ANONYMISE,
                "obj_pk": ["{}-{}".format(content_type, obj_1.pk)],
            },
            follow=True,
        )

        obj_1.refresh_from_db()
        obj_2.refresh_from_db()
        self.assertTrue(obj_1.is_anonymised())
        self.assertFalse(obj_2.is_anonymised())

        self.assertEqual(response.redirect_chain, [(tool_root_url, 302)])

    def test_anonymise____can_anonymise_disabled__not_all_records_anonymised(self):
        obj_1 = baker.make(FirstSearchModel, email="an@example.com")
        obj_1.anonymise()
        obj_4 = baker.make(ForthSearchModel, email="an@example.com")
        content_type_1 = ContentType.objects.get_for_model(FirstSearchModel).pk
        content_type_4 = ContentType.objects.get_for_model(ForthSearchModel).pk

        response = self.client.post(
            tool_root_url,
            {
                "term": "an@example.com",
                "action": gdpr_assist.admin.tool.PersonalDataSearchForm.ACTION_ANONYMISE,
                "obj_pk": [
                    "{}-{}".format(content_type_1, obj_1.pk),
                    "{}-{}".format(content_type_4, obj_4.pk),
                ],
            },
            follow=True,
        )

        obj_1.refresh_from_db()
        obj_4.refresh_from_db()
        self.assertTrue(obj_1.is_anonymised())
        self.assertFalse(obj_4.is_anonymised())

        self.assertEqual(response.redirect_chain, [(tool_root_url, 302)])

    def test_warn_will_not_anonymise__present(self):
        baker.make(ForthSearchModel, email="an@example.com")

        response = self.client.post(tool_root_url, {"term": "an@example.com"})

        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "These records will not be anonymised")

    def test_warn_will_not_anonymise__not_present(self):
        baker.make(FirstSearchModel, email="an@example.com")

        response = self.client.post(tool_root_url, {"term": "an@example.com"})

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "These records will not be anonymised")

    def test_export_no_matches__reports_error(self):
        # Request an object we know doesn't exist
        self.assertEqual(FirstSearchModel.objects.count(), 0)
        response = self.client.post(
            tool_root_url,
            {
                "term": "one@example.com",
                "action": gdpr_assist.admin.tool.PersonalDataSearchForm.ACTION_EXPORT,
                "obj_pk": [
                    "{}-1".format(
                        ContentType.objects.get_for_model(FirstSearchModel).pk
                    )
                ],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<li class="error">No objects selected</li>')

    def test_export_matches__records_export(self):
        # Creating 4 records:
        # * One matching in FirstSearchModel so we collect multiple models
        # * One not matching in FirstSearchModel so we exclude ignored records
        # * Two in SecondSearchModel so we collect multiple records
        obj_1 = FirstSearchModel.objects.create(chars="test1", email="one@example.com")
        obj_2 = FirstSearchModel.objects.create(chars="test2", email="two@example.com")
        obj_3 = SecondSearchModel.objects.create(chars="test3", email="one@example.com")
        obj_4 = SecondSearchModel.objects.create(chars="test4", email="one@example.com")
        content_type_1 = ContentType.objects.get_for_model(FirstSearchModel).pk
        content_type_2 = ContentType.objects.get_for_model(SecondSearchModel).pk

        response = self.client.post(
            tool_root_url,
            {
                "term": "one@example.com",
                "action": gdpr_assist.admin.tool.PersonalDataSearchForm.ACTION_EXPORT,
                "obj_pk": [
                    "{}-{}".format(content_type_1, obj_1.pk),
                    "{}-{}".format(content_type_2, obj_3.pk),
                    "{}-{}".format(content_type_2, obj_4.pk),
                ],
            },
            follow=True,
        )

        # Check they didn't get anonymised by mistake
        obj_1.refresh_from_db()
        obj_2.refresh_from_db()
        obj_3.refresh_from_db()
        obj_4.refresh_from_db()
        self.assertFalse(obj_1.is_anonymised())
        self.assertFalse(obj_2.is_anonymised())
        self.assertFalse(obj_3.is_anonymised())
        self.assertFalse(obj_4.is_anonymised())

        # Download zip into memory and check it's as expected
        zip_data = BytesIO()
        zip_data.write(response.content)
        zip_file = zipfile.ZipFile(zip_data)
        self.assertEqual(
            sorted(zip_file.namelist()),
            ["second_search.csv", "tests_app-FirstSearchModel.csv"],
        )

        mode = "r"

        with zip_file.open("tests_app-FirstSearchModel.csv", mode) as f:
            reader = csv.DictReader(TextIOWrapper(f))
            self.assertEqual(reader.fieldnames, ["email"])
            rows = list(reader)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["email"], "one@example.com")

        with zip_file.open("second_search.csv", mode) as f:
            reader = csv.DictReader(TextIOWrapper(f))
            self.assertEqual(sorted(reader.fieldnames), ["chars", "email"])
            rows = list(reader)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["chars"], "test3")
            self.assertEqual(rows[0]["email"], "one@example.com")
            self.assertEqual(rows[1]["chars"], "test4")
            self.assertEqual(rows[1]["email"], "one@example.com")
