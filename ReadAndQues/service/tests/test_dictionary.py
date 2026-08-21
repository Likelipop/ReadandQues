import unittest

from service.dictionary import lookup_word


class DictionaryServiceTests(unittest.TestCase):
    def test_lookup_pedagogical(self):
        res = lookup_word("pedagogical")
        self.assertTrue(res["found"])
        self.assertEqual(res["word"], "pedagogical")
        self.assertGreaterEqual(len(res["definitions"]), 1)
        self.assertIn("educational", res["definitions"][0]["synonyms"])

    def test_lookup_mitigate(self):
        res = lookup_word("mitigate")
        self.assertTrue(res["found"])
        self.assertEqual(res["word"], "mitigate")
        self.assertGreaterEqual(len(res["definitions"]), 1)
        self.assertIn("alleviate", res["definitions"][0]["synonyms"])

    def test_lookup_wordnet_word(self):
        res = lookup_word("science")
        self.assertTrue(res["found"])
        self.assertGreaterEqual(len(res["definitions"]), 1)

    def test_lookup_empty_word(self):
        res = lookup_word("   ")
        self.assertFalse(res["found"])
        self.assertEqual(len(res["definitions"]), 0)
