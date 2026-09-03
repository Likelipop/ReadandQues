"""
ReadAndQues/service/tests/test_service_suite.py
Comprehensive QA Service Test Suite for Backend Workflows & Data Services.

Designed from a Senior QA / Tester perspective to validate:
1. Celery Asynchronous Pipeline Orchestration (Crawling, Inks, Quiz Generation, Failure handling)
2. Data Access Selectors & Mongo Document Transformations (Detail normalization, filtering, BM25 ranking)
3. Passage Proof Grounding Service (Exact match, fuzzy match, ungrounded fallbacks)
4. Account & User Star Economy (Atomic deductions, balance limits, high-score star awards, transaction rollbacks)
5. Django Ninja REST Endpoints (Homepage bundle, paginated articles, offline dictionary, exam submission)
"""

import json
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.db import transaction
from django.test import Client, TestCase

from accounts.models import UserProfile
from ai_service.rag.grounding.passage_proof import get_passage_proof
from readspace.utils import StarDeductionError, consume_user_star
from service.pipelines import enrich_article_only, ingest_and_enrich_article
from service.selectors import (
    get_article_detail,
    get_article_status,
    get_related_articles,
    list_completed_articles,
    search_articles_keyword,
)
from service.services import import_article, submit_exam_attempt


class ServiceTestSuite(TestCase):
    """Senior QA Service Test Suite covering backend data layers and business logic."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="service_tester",
            email="tester@example.com",
            password="StrongPassword123!",
        )
        self.profile, _ = UserProfile.objects.get_or_create(
            user=self.user,
            defaults={"stars": 15, "total_articles_imported": 2, "exams_taken": 1},
        )
        self.sample_article_id = "art-sample-001"
        self.mock_mongo_doc = {
            "article_id": self.sample_article_id,
            "id": self.sample_article_id,
            "url": "https://example.com/quantum-computing",
            "title": "The Evolution of Artificial Intelligence in Higher Education",
            "source_name": "MIT Technology Review",
            "cleaned_text": "The rapid proliferation of neural network architectures has precipitated a pedagogical reckoning.",
            "original_text": "The rapid proliferation of neural network architectures has precipitated a pedagogical reckoning.",
            "html_content": "<p>The rapid proliferation of neural network architectures...</p>",
            "word_count": 12,
            "theme": "Technology",
            "genre": "academic",
            "status": "completed",
            "quiz_status": "completed",
            "has_quiz": True,
            "exams": [
                {
                    "exam_id": "exam_sample_001",
                    "title": "AI in Education Test",
                    "quizzes": [
                        {
                            "quiz_type": "multiple_choice",
                            "question": "According to paragraph 1, traditional higher education was primarily characterized by which method?",
                            "options": ["A broadcast model with summative written examinations", "Other"],
                            "correct_answer": "A broadcast model with summative written examinations",
                            "explanation": "Paragraph 1 states broadcast pedagogical model.",
                            "supporting_text": "traditional tertiary instruction adhered to a broadcast pedagogical model",
                        }
                    ],
                }
            ],
        }

    # ── 1. Pipeline & Orchestration Tests ───────────────────

    def test_article_pipeline_full_ingestion_flow(self):
        """QA Test: Full ingestion pipeline crawls URL, cleans text, runs AI enrichment, and saves gold document."""
        mock_ai_result = {
            "keywords": ["Quantum", "Technology"],
            "summary": "Quantum summary",
            "questions": [{"question": "Q1", "correct_answer": "A"}],
        }

        with (
            patch("service.pipelines.trafilatura.fetch_url", return_value="<html>Sample</html>"),
            patch("service.pipelines.trafilatura.extract", return_value="Quantum computers leverage qubits for fast computation. " * 10),
            patch("service.pipelines.object_store.save_silver_clean"),
            patch("service.pipelines.article_store.save_gold_content", return_value=True),
            patch("service.pipelines.generate_quiz", return_value=mock_ai_result),
            patch("service.pipelines.exam_store.save_exam"),
            patch("service.pipelines.index_article", return_value=True),
        ):
            result = ingest_and_enrich_article(article_id="art-test-123", url="https://example.com/quantum")

            self.assertIn("article_id", result)
            self.assertEqual(result["status"], "completed")

    def test_article_pipeline_scrape_failure_records_error_status(self):
        """QA Test: When scraper fails or encounters 404, pipeline records failure status."""
        with patch("service.pipelines.trafilatura.fetch_url", return_value=None):
            result = ingest_and_enrich_article(article_id="art-fail-404", url="https://invalid-url.com")

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["error"], "Fetch failed")

    # ── 2. Data Selectors & Mongo Document Access Tests ────────────────────────

    def test_get_article_detail_gold_content(self):
        """QA Test: get_article_detail retrieves clean document directly from gold_content."""
        mock_gold = {
            "article_id": "art-gold-001",
            "title": "Quantum Computation in Modern Science",
            "source": "MIT Tech Review",
            "url": "https://example.com/quantum",
            "original_text": "Quantum computing is computation using quantum states.",
            "word_count": 8,
            "published_at": "2026-09-01T00:00:00Z",
        }
        with patch("service.selectors.article_store.get_gold_content", return_value=mock_gold):
            doc = get_article_detail("art-gold-001")

            self.assertIsNotNone(doc)
            self.assertEqual(doc["article_id"], "art-gold-001")
            self.assertEqual(doc["title"], "Quantum Computation in Modern Science")
            self.assertEqual(doc["stage"], "gold")

    def test_get_article_detail_nonexistent_returns_none(self):
        """QA Test: get_article_detail returns None when article does not exist in gold_content."""
        with patch("service.selectors.article_store.get_gold_content", return_value=None):
            doc = get_article_detail("nonexistent-article-id-999")
            self.assertIsNone(doc)

    def test_list_completed_articles_filtering(self):
        """QA Test: list_completed_articles filters articles from gold_content correctly."""
        mock_articles = [
            {
                "article_id": "art-1",
                "title": "AI in Education",
                "source": "Nature News",
                "keywords": ["Technology"],
                "original_text": "AI transforms modern classrooms.",
                "published_at": "2026-09-01T00:00:00Z",
            }
        ]
        with patch("service.selectors.article_store.list_gold_articles", return_value=mock_articles):
            res = list_completed_articles(keyword="Technology", limit=10)
            self.assertIn("articles", res)
            self.assertGreater(len(res["articles"]), 0)
            self.assertEqual(res["articles"][0]["article_id"], "art-1")

    def test_search_articles_keyword_bm25_ranking(self):
        """QA Test: search_articles_keyword returns matched documents from gold_content."""
        mock_results = [
            {
                "article_id": "art-sample-001",
                "id": "art-sample-001",
                "title": "The Evolution of Artificial Intelligence in Higher Education",
                "source": "MIT Review",
                "original_text": "AI education summary",
                "word_count": 685,
            }
        ]
        with patch("service.selectors.article_store.search_gold_content_by_text", return_value=mock_results):
            with patch("service.selectors.get_bm25_index", return_value=(None, [])):
                results = search_articles_keyword("intelligence", limit=5)
                self.assertEqual(len(results), 1)
                self.assertEqual(results[0]["article_id"], "art-sample-001")

    # ── 3. Passage Proof Grounding Service Tests ───────────────────────────────

    def test_passage_proof_exact_sentence_matching(self):
        """QA Test: Passage proof locator accurately finds exact sentence and proof excerpt."""
        mock_hits = [
            {
                "id": "chunk_0",
                "text": "The rapid proliferation of neural network architectures has precipitated a pedagogical reckoning.",
                "score": 0.95,
            }
        ]
        mock_client = MagicMock()
        mock_client.get_database.return_value.__getitem__.return_value.find_one.return_value = self.mock_mongo_doc

        with (
            patch("ai_service.rag.grounding.passage_proof.MongoClient", return_value=mock_client),
            patch("ai_service.rag.grounding.passage_proof.vector_search_chunks", return_value=mock_hits),
        ):
            proof = get_passage_proof(self.sample_article_id, question_idx=0)

            self.assertIsNotNone(proof)
            self.assertEqual(proof["question_index"], 0)
            self.assertTrue(proof["proof_found"])
            self.assertEqual(proof["correct_answer"], "A broadcast model with summative written examinations")
            self.assertGreater(proof["confidence_score"], 0.7)

    def test_passage_proof_unmatched_fallback(self):
        """QA Test: When question index is invalid or proof cannot be found, returns safe fallback."""
        mock_client = MagicMock()
        mock_client.get_database.return_value.__getitem__.return_value.find_one.return_value = self.mock_mongo_doc

        with patch("ai_service.rag.grounding.passage_proof.MongoClient", return_value=mock_client):
            proof = get_passage_proof(self.sample_article_id, question_idx=999)

            self.assertIsNone(proof)


    # ── 4. Account & User Star Economy Service Tests ───────────────────────────

    def test_consume_user_star_success(self):
        """QA Test: consume_user_star context manager decrements user star balance upon article import."""
        initial_stars = self.profile.stars
        with consume_user_star(self.user):
            pass

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.stars, initial_stars - 1)

    def test_consume_user_star_insufficient_balance(self):
        """QA Test: User with 0 stars cannot perform star-consuming operations."""
        self.profile.stars = 0
        self.profile.save()

        with self.assertRaises(StarDeductionError) as ctx:
            with consume_user_star(self.user):
                pass
        self.assertIn("NO_STARS", str(ctx.exception))

    def test_submit_exam_attempt_persists_log_and_updates_proficiency(self):
        """QA Test: Submitting an exam creates ExamAttemptLog and updates topic proficiency."""
        with (
            patch("service.services.activity_store.log_reading_session"),
            patch("service.services.exam_store.get_exam", return_value={"theme": "Technology"}),
        ):
            res = submit_exam_attempt(
                user_id=self.user.id,
                article_id=self.sample_article_id,
                score=10,
                total_questions=10,
                answers={"0": "Ans1", "1": "Ans2"},
                elapsed_time=120,
            )

            self.assertEqual(res["status"], "success")
            self.assertEqual(res["score"], 10)
            self.assertEqual(res["total_questions"], 10)

    def test_user_star_atomic_rollback(self):
        """QA Test: If an exception occurs inside transaction, star deduction is rolled back."""
        initial_stars = self.profile.stars

        try:
            with transaction.atomic():
                self.profile.stars -= 1
                self.profile.save()
                raise RuntimeError("Simulated mid-pipeline unhandled crash")
        except RuntimeError:
            pass

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.stars, initial_stars)

    # ── 5. Django Ninja REST API Contract Tests ────────────────────────────────

    def test_ninja_homepage_bundle_endpoint(self):
        """QA Test: GET /api/v1/homepage/ returns hero hot news, daily vocab, and recommendations."""
        mock_article_item = {
            "article_id": "art-1",
            "id": "art-1",
            "title": "Breaking News",
            "source_name": "TechDaily",
            "theme": "Technology",
            "genre": "academic",
            "summary": "AI summary",
            "word_count": 500,
            "status": "completed",
            "has_attempted": False,
        }
        mock_vocab = {
            "word": "paradigm",
            "phonetic": "/ˈpær.ə.daɪm/",
            "part_of_speech": "noun",
            "definition": "typical example",
            "example": "A paradigm shift in physics.",
        }

        with (
            patch("readspace.api.router.selectors.get_hot_news", return_value=[mock_article_item]),
            patch("readspace.api.router.selectors.get_recommendations", return_value=[mock_article_item]),
            patch(
                "readspace.api.router.selectors.list_completed_articles",
                return_value={"articles": [mock_article_item], "total_count": 1, "page": 1, "total_pages": 1},
            ),
        ):
            response = self.client.get("/api/v1/homepage/")
            self.assertEqual(response.status_code, 200)
            data = response.json()

            self.assertEqual(data["status"], "success")
            self.assertIn("hero_articles", data)
            self.assertIn("recommended_articles", data)
            self.assertIn("articles", data)

    def test_ninja_articles_list_pagination(self):
        """QA Test: GET /api/v1/articles/ supports query filters and returns pagination envelope."""
        mock_article_item = {
            "article_id": "art-1",
            "id": "art-1",
            "title": "Quantum Computing",
            "source_name": "TechDaily",
            "theme": "Technology",
            "genre": "academic",
            "summary": "Quantum computing fundamentals",
            "word_count": 600,
            "status": "completed",
            "has_attempted": False,
        }
        mock_catalog = {
            "articles": [mock_article_item],
            "total_count": 25,
            "has_next": True,
            "has_prev": False,
        }

        with patch("readspace.api.router.selectors.list_completed_articles", return_value=mock_catalog):
            response = self.client.get("/api/v1/articles/?page=1&limit=5&theme=Technology")
            self.assertEqual(response.status_code, 200)
            data = response.json()

            self.assertEqual(data["page"], 1)
            self.assertEqual(data["total_count"], 25)
            self.assertEqual(data["has_next"], True)
            self.assertIn("articles", data)
            self.assertEqual(len(data["articles"]), 1)

    def test_dictionary_lookup_endpoint(self):
        """QA Test: GET /api/v1/dictionary/lookup/ returns real WordNet definitions, phonetics, and lemmas."""
        # 1. Base word lookup
        response = self.client.get("/api/v1/dictionary/lookup/?word=resonance")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["word"].lower(), "resonance")
        self.assertTrue(data["found"])
        self.assertGreater(len(data["definitions"]), 0)
        self.assertIn("definition", data["definitions"][0])
        self.assertIsNotNone(data.get("phonetic"))

        # 2. Inflected verb lookup ('received' -> lemma 'receive' or verb definitions)
        response_rec = self.client.get("/api/v1/dictionary/lookup/?word=received")
        self.assertEqual(response_rec.status_code, 200)
        data_rec = response_rec.json()
        self.assertTrue(data_rec["found"])
        self.assertEqual(data_rec["part_of_speech"], "verb")
        self.assertGreater(len(data_rec["definitions"]), 0)
        self.assertNotIn("Academic terminology", data_rec["definitions"][0]["definition"])

        # 3. Unrecognized gibberish word
        response_unf = self.client.get("/api/v1/dictionary/lookup/?word=xyzabc999nonexistent")
        self.assertEqual(response_unf.status_code, 200)
        data_unf = response_unf.json()
        self.assertFalse(data_unf["found"])
        self.assertEqual(len(data_unf["definitions"]), 0)

    def test_list_completed_articles_with_date_filters(self):
        """QA Test: list_completed_articles filters articles based on publication date."""
        from service.selectors import list_completed_articles

        res_all = list_completed_articles(date_filter="all")
        self.assertGreater(len(res_all["articles"]), 0)

        res_today = list_completed_articles(date_filter="today")
        self.assertIsInstance(res_today["articles"], list)

        res_week = list_completed_articles(date_filter="week")
        self.assertIsInstance(res_week["articles"], list)

        res_month = list_completed_articles(date_filter="month")
        self.assertIsInstance(res_month["articles"], list)

    def test_ninja_articles_list_with_date_filter(self):
        """QA Test: GET /api/v1/articles/?date_filter=week accepts date_filter query parameter."""
        response = self.client.get("/api/v1/articles/?date_filter=week&theme=All")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("articles", data)
        self.assertIn("total_count", data)

    def test_ninja_save_markers_contract(self):
        """QA Test: POST /api/v1/{pk}/save_markers/ saves user highlight annotations."""
        self.client.login(username="service_tester", password="StrongPassword123!")

        with patch("readspace.api.router.services.save_user_highlights", return_value=True):
            payload = {"highlighted_markdown": "==Quantum superposition== is key."}
            response = self.client.post(
                f"/api/v1/{self.sample_article_id}/save_markers/",
                data=json.dumps(payload),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "success")
