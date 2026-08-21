"""Tests for offline NLTK WordNet dictionary service and API endpoint."""
from django.test import TestCase
from ninja.testing import TestClient
from readspace.api.router import api
from service.dictionary import lookup_word


class DictionaryTests(TestCase):
    def setUp(self):
        self.client = TestClient(api)

    def test_lookup_word_direct_service(self):
        res = lookup_word("pedagogical")
        self.assertTrue(res["found"])
        self.assertEqual(res["word"], "pedagogical")
        self.assertGreater(len(res["definitions"]), 0)
        self.assertIn("educational", res["definitions"][0]["synonyms"])

    def test_lookup_word_api_endpoint(self):
        response = self.client.get("/dictionary/lookup/?word=mitigate")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["found"])
        self.assertEqual(data["word"], "mitigate")
        self.assertGreater(len(data["definitions"]), 0)

    def test_lookup_word_missing_query_param(self):
        response = self.client.get("/dictionary/lookup/?word=")
        self.assertEqual(response.status_code, 400)
