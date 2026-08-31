from shared.schemas import Article, generate_article_id
from shared.enums import Status


class DataIntegrityContractsTests(TestCase):
    def test_generate_article_id_is_deterministic_for_url(self):
        url = "https://example.com/test-article"
        id1 = generate_article_id(url)
        id2 = generate_article_id(url)
        self.assertEqual(id1, id2)
        self.assertTrue(id1.startswith("art_"))

    def test_article_contract_defaults(self):
        contract = ArticleContract(article_id="art_123", url="https://example.com/a")
        self.assertEqual(contract.status, ArticleStatus.CRAWLING)
        self.assertEqual(contract.ai_status, AIStatus.PENDING_GENERATION)
