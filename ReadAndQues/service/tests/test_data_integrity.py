from unittest import TestCase

from service.domain.contracts import ArticleContract, generate_article_id
from service.domain.enums import AIStatus, ArticleStatus


class DataIntegrityContractsTests(TestCase):
    def test_generate_article_id_is_deterministic_for_url(self):
        url = "https://example.com/test-article"
        id1 = generate_article_id(url)
        id2 = generate_article_id(url)
        self.assertEqual(id1, id2)
        self.assertTrue(id1.startswith("art_"))

    def test_article_contract_defaults(self):
        contract = ArticleContract(
            article_id="art_123",
            url="https://example.com/a"
        )
        self.assertEqual(contract.status, ArticleStatus.CRAWLING)
        self.assertEqual(contract.ai_status, AIStatus.PENDING_GENERATION)
