"""
Test admin tools
"""
from io import BytesIO, TextIOWrapper
import csv
import zipfile

import django
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import Client, TestCase

from model_mommy import mommy

import gdpr_assist

from .gdpr_assist_tests_app.models import (
    ModelWithPrivacyMeta,
    FirstSearchModel,
    SecondSearchModel,
)


model_root_url = '/admin/gdpr_assist_tests_app/modelwithprivacymeta/'
tool_root_url = '/admin/gdpr_assist/personaldata/'


class AdminTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        user = User.objects.create_superuser(
            username='test',
            email='test@example.com',
            password='test',
        )

        if django.VERSION <= (1, 9):
            # Django 1.8 support - no client.force_login
            self.client.login(username='test', password='test')
        else:
            # Django 1.9+
            self.client.force_login(user)


class TestModelAdmin(AdminTestCase):
    def test_changelist__anonymise_action_present(self):
        mommy.make(ModelWithPrivacyMeta)
        response = self.client.get(model_root_url)
        self.assertContains(response, '<option value="anonymise">')

    def test_anonymise_action_submit__redirect_to_anonymise_view(self):
        obj_1 = mommy.make(ModelWithPrivacyMeta)
        obj_2 = mommy.make(ModelWithPrivacyMeta)

        response = self.client.post(
            model_root_url,
            {
                'action': 'anonymise',
                '_selected_action': [obj_1.pk, obj_2.pk],
            },
            follow=True,
        )

        test_url = '{root_url}anonymise/?ids={pk1},{pk2}'.format(
            root_url=model_root_url,
            pk1=obj_1.pk,
            pk2=obj_2.pk,
        )

        if django.VERSION <= (1, 9):
            # Django 1.8 support - redirects include host
            self.assertEqual(len(response.redirect_chain), 1)
            self.assertTrue(response.redirect_chain[0][0].endswith(
                test_url
            ))
            self.assertEqual(response.redirect_chain[0][1], 302)
        else:
            # Django 1.9+
            self.assertEqual(
                response.redirect_chain,
                [(test_url, 302)],
            )
        self.assertContains(
            response,
            '<p>Are you sure you want to anonymise the following Model With Privacy Metas:</p>',
        )
        self.assertContains(
            response,
            '<input type="hidden" name="ids" value="{pk1},{pk2}">'.format(
                pk1=obj_1.pk,
                pk2=obj_2.pk,
            ),
        )

    def test_anonymise_view_submit__redirect_to_anonymise_view(self):
        obj_1 = mommy.make(ModelWithPrivacyMeta, anonymised=False)
        obj_2 = mommy.make(ModelWithPrivacyMeta, anonymised=False)

        response = self.client.post(
            model_root_url + 'anonymise/',
            {
                'ids': ','.join([str(obj_1.pk), str(obj_2.pk)]),
            },
            follow=True,
        )
        obj_1.refresh_from_db()
        obj_2.refresh_from_db()
        self.assertTrue(obj_1.anonymised)
        self.assertTrue(obj_2.anonymised)

        if django.VERSION <= (1, 9):
            # Django 1.8 support - redirects include host
            self.assertEqual(len(response.redirect_chain), 1)
            self.assertTrue(response.redirect_chain[0][0].endswith(model_root_url))
            self.assertEqual(response.redirect_chain[0][1], 302)
        else:
            # Django 1.9+
            self.assertEqual(
                response.redirect_chain,
                [(model_root_url, 302)],
            )

        self.assertContains(
            response,
            '<li class="success">2 Model With Privacy Metas anonymised</li>',
        )


class TestAdminTool(AdminTestCase):
    def test_tool_is_available(self):
        mommy.make(FirstSearchModel)
        response = self.client.get(tool_root_url)
        self.assertContains(response, '<h1>Personal Data</h1>')

    def test_search__returns_correct_results(self):
        obj_1 = mommy.make(
            FirstSearchModel,
            email='one@example.com',
        )
        mommy.make(
            FirstSearchModel,
            email='two@example.com',
        )

        response = self.client.post(tool_root_url, {'term': 'one@example.com'})
        self.assertContains(
            response,
            '<h2>Gdpr_Assist_Tests_App: First Search Model</h2>',
        )
        self.assertContains(
            response,
            '<input name="obj_pk" value="{}-{}" class="action-select" type="checkbox">'.format(
                ContentType.objects.get_for_model(FirstSearchModel).pk,
                obj_1.pk,
            ),
        )

    def test_anonymise__records_anonymised(self):
        obj_1 = mommy.make(
            FirstSearchModel,
            email='one@example.com',
            anonymised=False,
        )
        obj_2 = mommy.make(
            FirstSearchModel,
            email='two@example.com',
            anonymised=False,
        )
        content_type = ContentType.objects.get_for_model(FirstSearchModel).pk

        response = self.client.post(
            tool_root_url,
            {
                'term': 'one@example.com',
                'action': gdpr_assist.admin.tool.PersonalDataSearchForm.ACTION_ANONYMISE,
                'obj_pk': ['{}-{}'.format(content_type, obj_1.pk)],
            },
            follow=True,
        )

        obj_1.refresh_from_db()
        obj_2.refresh_from_db()
        self.assertTrue(obj_1.anonymised)
        self.assertFalse(obj_2.anonymised)

        if django.VERSION <= (1, 9):
            # Django 1.8 support - redirects include host
            self.assertEqual(len(response.redirect_chain), 1)
            self.assertTrue(response.redirect_chain[0][0].endswith(tool_root_url))
            self.assertEqual(response.redirect_chain[0][1], 302)
        else:
            # Django 1.9+
            self.assertEqual(
                response.redirect_chain,
                [(tool_root_url, 302)],
            )

    def test_export_no_matches__reports_error(self):
        # Request an object we know doesn't exist
        self.assertEqual(FirstSearchModel.objects.count(), 0)
        response = self.client.post(
            tool_root_url,
            {
                'term': 'one@example.com',
                'action': gdpr_assist.admin.tool.PersonalDataSearchForm.ACTION_EXPORT,
                'obj_pk': [
                    '{}-1'.format(
                        ContentType.objects.get_for_model(FirstSearchModel).pk,
                    ),
                ],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            '<li class="error">No objects selected</li>',
        )

    def test_export_matches__records_export(self):
        # Creating 4 records:
        # * One matching in FirstSearchModel so we collect multiple models
        # * One not matching in FirstSearchModel so we exclude ignored records
        # * Two in SecondSearchModel so we collect multiple records
        obj_1 = FirstSearchModel.objects.create(
            chars='test1',
            email='one@example.com',
            anonymised=False,
        )
        obj_2 = FirstSearchModel.objects.create(
            chars='test2',
            email='two@example.com',
            anonymised=False,
        )
        obj_3 = SecondSearchModel.objects.create(
            chars='test3',
            email='one@example.com',
            anonymised=False,
        )
        obj_4 = SecondSearchModel.objects.create(
            chars='test4',
            email='one@example.com',
            anonymised=False,
        )
        content_type_1 = ContentType.objects.get_for_model(FirstSearchModel).pk
        content_type_2 = ContentType.objects.get_for_model(SecondSearchModel).pk

        response = self.client.post(
            tool_root_url,
            {
                'term': 'one@example.com',
                'action': gdpr_assist.admin.tool.PersonalDataSearchForm.ACTION_EXPORT,
                'obj_pk': [
                    '{}-{}'.format(content_type_1, obj_1.pk),
                    '{}-{}'.format(content_type_2, obj_3.pk),
                    '{}-{}'.format(content_type_2, obj_4.pk),
                ],
            },
            follow=True,
        )

        # Check they didn't get anonymised by mistake
        obj_1.refresh_from_db()
        obj_2.refresh_from_db()
        obj_3.refresh_from_db()
        obj_4.refresh_from_db()
        self.assertFalse(obj_1.anonymised)
        self.assertFalse(obj_2.anonymised)
        self.assertFalse(obj_3.anonymised)
        self.assertFalse(obj_4.anonymised)

        # Download zip into memory and check it's as expected
        zip_data = BytesIO()
        zip_data.write(response.content)
        zip_file = zipfile.ZipFile(zip_data)
        self.assertEqual(
            sorted(zip_file.namelist()),
            [
                'gdpr_assist_tests_app-FirstSearchModel.csv',
                'second_search.csv',
            ],
        )

        mode = 'r'

        with zip_file.open(
            'gdpr_assist_tests_app-FirstSearchModel.csv',
            mode,
        ) as f:
            reader = csv.DictReader(TextIOWrapper(f))
            self.assertEqual(
                reader.fieldnames,
                ['email'],
            )
            rows = list(reader)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['email'], 'one@example.com')

        with zip_file.open('second_search.csv', mode) as f:
            reader = csv.DictReader(TextIOWrapper(f))
            self.assertEqual(
                sorted(reader.fieldnames),
                ['chars', 'email'],
            )
            rows = list(reader)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]['chars'], 'test3')
            self.assertEqual(rows[0]['email'], 'one@example.com')
            self.assertEqual(rows[1]['chars'], 'test4')
            self.assertEqual(rows[1]['email'], 'one@example.com')
