"""
Test search

See test_admin_tool.py for admin search view tests
"""
from django.test import TestCase

from model_mommy import mommy

from gdpr_assist.registry import registry

from .gdpr_assist_tests_app.models import (
    ModelWithPrivacyMeta,
    FirstSearchModel,
    SecondSearchModel,
)


class TestPrivacyMetaSearch(TestCase):
    def test_search_no_fields_registered__returns_empty_queryset(self):
        mommy.make(ModelWithPrivacyMeta, email='test@example.com')
        results = ModelWithPrivacyMeta._privacy_meta.search('test@example.com')
        self.assertEqual(results.count(), 0)

    def test_search__finds_match__ignores_miss(self):
        expected = mommy.make(FirstSearchModel, email='test@example.com')
        mommy.make(FirstSearchModel, email='miss@example.com')

        results = FirstSearchModel._privacy_meta.search('test@example.com')
        self.assertEqual(results.count(), 1)
        self.assertEqual(results[0].pk, expected.pk)

    def test_search__finds_multiple_matches__ignores_misses(self):
        expected_1 = mommy.make(FirstSearchModel, email='test@example.com')
        expected_2 = mommy.make(FirstSearchModel, email='test@example.com')
        mommy.make(FirstSearchModel, email='miss@example.com')
        mommy.make(FirstSearchModel, email='miss@example.com')

        results = FirstSearchModel._privacy_meta.search('test@example.com')
        self.assertEqual(results.count(), 2)
        self.assertListEqual(
            sorted(results.values_list('pk', flat=True)),
            sorted([expected_1.pk, expected_2.pk]),
        )


class TestRegistrySearch(TestCase):
    def test_search__finds_match_first_model__ignores_misses(self):
        expected = mommy.make(FirstSearchModel, email='test@example.com')
        mommy.make(FirstSearchModel, email='miss@example.com')
        mommy.make(SecondSearchModel, email='miss@example.com')

        full_results = registry.search('test@example.com')
        self.assertEqual(len(full_results), 1)

        model, results = full_results[0]
        self.assertEqual(model, FirstSearchModel)
        self.assertEqual(results.count(), 1)
        self.assertEqual(results[0].pk, expected.pk)

    def test_search__finds_match_second_model__ignores_misses(self):
        expected = mommy.make(SecondSearchModel, email='test@example.com')
        mommy.make(FirstSearchModel, email='miss@example.com')
        mommy.make(SecondSearchModel, email='miss@example.com')

        full_results = registry.search('test@example.com')
        self.assertEqual(len(full_results), 1)

        model, results = full_results[0]
        self.assertEqual(model, SecondSearchModel)
        self.assertEqual(results.count(), 1)
        self.assertEqual(results[0].pk, expected.pk)

    def test_search__finds_matches_multiple_models__ignores_misses(self):
        expected_1 = mommy.make(FirstSearchModel, email='test@example.com')
        expected_2 = mommy.make(FirstSearchModel, email='test@example.com')
        expected_3 = mommy.make(SecondSearchModel, email='test@example.com')
        expected_4 = mommy.make(SecondSearchModel, email='test@example.com')
        mommy.make(FirstSearchModel, email='miss@example.com')
        mommy.make(SecondSearchModel, email='miss@example.com')

        full_results = registry.search('test@example.com')
        self.assertEqual(len(full_results), 2)

        # Sort full results into testable order
        model_0, results_0 = full_results[0]
        model_1, results_1 = full_results[1]

        if model_0 is SecondSearchModel:
            model_0, results_0, model_1, results_1 = (
                model_1, results_1, model_0, results_0,
            )

        self.assertEqual(model_0, FirstSearchModel)
        self.assertEqual(results_0.count(), 2)
        self.assertEqual(results_0[0].pk, expected_1.pk)
        self.assertEqual(results_0[1].pk, expected_2.pk)

        self.assertEqual(model_1, SecondSearchModel)
        self.assertEqual(results_1.count(), 2)
        self.assertEqual(results_1[0].pk, expected_3.pk)
        self.assertEqual(results_1[1].pk, expected_4.pk)
