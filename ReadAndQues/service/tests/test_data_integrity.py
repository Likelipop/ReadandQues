from unittest import TestCase
from service.domain.contracts import ArticleContract, ExamAttemptContract, generate_article_id
from service.domain.enums import ArticleStatus, AIStatus
from service.repositories.article_repository import LegacyArticleReadAdapter


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

    def test_legacy_read_adapter_normalizes_raw_dict(self):
        legacy_doc = {
            "_id": "507f1f77bcf86cd799439011",
            "url": "https://example.com/legacy",
            "title": "Legacy Title",
            "status": "completed",
            "ai_status": "completed",
        }
        contract = LegacyArticleReadAdapter.to_contract(legacy_doc)
        self.assertEqual(contract.article_id, "507f1f77bcf86cd799439011")
        self.assertEqual(contract.status, ArticleStatus.COMPLETED)
        self.assertEqual(contract.ai_status, AIStatus.COMPLETED)
