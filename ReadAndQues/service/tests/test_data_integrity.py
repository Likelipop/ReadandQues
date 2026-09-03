from unittest import TestCase

from shared.schemas import Article, generate_article_id


class DataIntegrityContractsTests(TestCase):
    def test_generate_article_id_is_deterministic_for_url(self):
        url = "https://example.com/test-article"
        id1 = generate_article_id(url)
        id2 = generate_article_id(url)
        self.assertEqual(id1, id2)
        self.assertTrue(id1.startswith("art_"))

    def test_article_contract_defaults(self):
        article = Article(article_id="art_123", url="https://example.com/a")
        self.assertEqual(article.article_id, "art_123")
        self.assertEqual(article.url, "https://example.com/a")
        self.assertEqual(article.keywords, [])
        self.assertEqual(article.exams, [])
