"""
ReadAndQues/readspace/tests/test_readspace_functional.py
Comprehensive functional tests for Readspace features, practices, and REST APIs.
"""

import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import UserProfile


class ReadspaceFunctionalTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="reading_pro",
            email="reading_pro@example.com",
            password="SecurePassword123!",
        )
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user, defaults={"stars": 10})
        self.article_id = "art-functional-test-001"
        self.mock_article_detail = {
            "article_id": self.article_id,
            "id": self.article_id,
            "url": "https://example.com/marine-life",
            "title": "The Impact of Microplastics on Marine Life",
            "source_name": "Marine Journal",
            "original_text": "Microplastics are tiny plastic particles that pollute the ocean.",
            "cleaned_text": "Microplastics are tiny plastic particles that pollute the ocean.",
            "html_content": "<p>Microplastics are tiny plastic particles that pollute the ocean.</p>",
            "word_count": 12,
            "theme": "Environment",
            "genre": "scientific",
            "summary": "Overview of marine microplastics.",
            "status": "completed",
            "quiz_status": "completed",
            "has_quiz": True,
            "exams": [
                {
                    "type": "multiple_choice",
                    "quizzes": [
                        {
                            "question": "What are microplastics?",
                            "options": ["Plastic particles", "Metals"],
                            "correct_answer": "Plastic particles",
                        }
                    ],
                }
            ],
        }

    # ── 1. Page View & Detail Navigation Tests ─────────────────────────────────

    def test_readspace_detail_authenticated_success(self):
        """Logged-in users can view full article reading workspace and questions."""
        self.client.login(username="reading_pro", password="SecurePassword123!")

        with (
            patch("service.selectors.get_article_detail", return_value=self.mock_article_detail),
            patch("service.selectors.get_related_articles", return_value=[]),
        ):
            response = self.client.get(reverse("readspace:readspace_detail", kwargs={"pk": self.article_id}))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "The Impact of Microplastics on Marine Life")

    def test_readspace_detail_redirects_anonymous_user(self):
        """Unauthenticated requests to readspace detail redirect to login."""
        response = self.client.get(reverse("readspace:readspace_detail", kwargs={"pk": self.article_id}))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_import_article_view_post_success(self):
        """Submitting a URL to import initiates the pipeline and redirects or returns status."""
        self.client.login(username="reading_pro", password="SecurePassword123!")

        mock_import_result = {
            "status": "created",
            "article_id": "new-art-100",
            "is_new": True,
        }
        with patch("service.services.import_article", return_value=mock_import_result):
            response = self.client.post(
                reverse("readspace:import_article"),
                data={"url": "https://example.com/marine-biology"},
                HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "started")
            self.assertEqual(data["id"], "new-art-100")

    def test_trigger_quiz_generation_api(self):
        """Trigger quiz generation view initiates background AI generation."""
        self.client.login(username="reading_pro", password="SecurePassword123!")

        with patch("service.services.trigger_quiz_generation", return_value={"status": "triggered"}):
            response = self.client.post(reverse("readspace:trigger_quiz", kwargs={"pk": self.article_id}))
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "processing")

    def test_article_status_polling_endpoint(self):
        """Status endpoint returns current pipeline processing state."""
        with patch(
            "service.selectors.get_article_status",
            return_value={"id": self.article_id, "status": "completed", "has_quiz": True, "error_message": ""},
        ):
            response = self.client.get(reverse("readspace:article_status", kwargs={"pk": self.article_id}))
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "completed")
            self.assertEqual(data["id"], self.article_id)

    # ── 2. Exam Submission & Practice Tools Tests ───────────────────────────────

    def test_submit_exam_attempt_functional_flow(self):
        """User answers submission persists attempt score and generates related content."""
        self.client.login(username="reading_pro", password="SecurePassword123!")

        submission_payload = {
            "score": 9.0,
            "total_questions": 10,
            "answers": {"0": "Plastic particles", "1": "TRUE"},
            "elapsed_time": 350,
            "highlighted_markdown": "==Microplastics==",
        }

        mock_attempt_result = {
            "status": "success",
            "attempt_id": "att-8888",
            "score": 9.0,
            "total_questions": 10,
        }

        with (
            patch("service.services.submit_exam_attempt", return_value=mock_attempt_result),
            patch("service.selectors.get_related_articles", return_value=[{"id": "art-002", "title": "Coral Reefs"}]),
        ):
            response = self.client.post(
                reverse("readspace:submit_exam_attempt", kwargs={"pk": self.article_id}),
                data=json.dumps(submission_payload),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "success")
            self.assertEqual(data["id"], "att-8888")
            self.assertIn("related_articles", data)
            self.assertEqual(data["related_articles"][0]["title"], "Coral Reefs")

    def test_save_markers_functional(self):
        """Save markers API persists user highlight annotations."""
        self.client.login(username="reading_pro", password="SecurePassword123!")

        with patch("service.services.save_user_highlights", return_value=True) as mock_save:
            payload = {"highlighted_markdown": "==Marine biology== is crucial."}
            response = self.client.post(
                reverse("readspace:save_markers", kwargs={"pk": self.article_id}),
                data=json.dumps(payload),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["status"], "success")
            mock_save.assert_called_once_with(
                user_id=self.user.id,
                article_id=self.article_id,
                highlighted_text="==Marine biology== is crucial.",
            )

    def test_passage_proof_grounding_functional(self):
        """Passage proof endpoint returns sentence index and quote for answer verification."""
        mock_proof = {
            "question_index": 0,
            "question_text": "What are microplastics?",
            "correct_answer": "Plastic particles",
            "proof_found": True,
            "proof_excerpt": "Microplastics are tiny plastic particles that pollute the ocean.",
            "confidence_score": 0.95,
        }

        with patch("ai_service.rag.grounding.get_passage_proof", return_value=mock_proof):
            response = self.client.get(reverse("readspace:passage_proof_api", kwargs={"pk": self.article_id, "idx": 0}))
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "success")
            self.assertEqual(data["proof"]["question_index"], 0)
            self.assertIn("Microplastics", data["proof"]["proof_excerpt"])

    def test_run_ai_tool_gateway_endpoint(self):
        """AI tool runner executes RAG question through gateway."""
        self.client.login(username="reading_pro", password="SecurePassword123!")

        mock_rag_result = {
            "status": "success",
            "answer": "Microplastics are particles under 5mm.",
            "citations": [],
        }

        with patch("service.services.ask_rag_question", return_value=mock_rag_result):
            payload = {
                "question": "What is the size of microplastics?",
                "article_id": self.article_id,
            }
            response = self.client.post(
                reverse("readspace:run_ai_tool_api"),
                data=json.dumps(payload),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "success")
            self.assertIn("particles under 5mm", data["answer"])

    # ── 3. Search & Discovery Endpoints ─────────────────────────────────────────

    def test_keyword_bm25_search(self):
        """BM25 keyword search returns ranked document matches."""
        mock_search_results = [
            {"article_id": "art-001", "title": "Ocean Microplastics", "score": 4.5},
            {"article_id": "art-002", "title": "Marine Habitats", "score": 2.1},
        ]

        with patch("service.selectors.search_articles_keyword", return_value=mock_search_results):
            response = self.client.get(reverse("readspace:search_bm25_api") + "?q=microplastics")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "success")
            self.assertEqual(len(data["results"]), 2)
            self.assertEqual(data["results"][0]["article_id"], "art-001")

    def test_semantic_vector_search(self):
        """Semantic vector search queries ChromaDB embeddings."""
        mock_semantic_results = [
            {"article_id": "art-001", "title": "Ocean Microplastics"},
        ]

        with patch("service.selectors.search_articles_semantic", return_value=mock_semantic_results):
            response = self.client.get(reverse("readspace:search_semantic_api") + "?q=plastic+debris+sea")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "success")
            self.assertEqual(data["results"][0]["article_id"], "art-001")

    # ── 4. Django Ninja Typed REST API Endpoints ───────────────────────────────

    def test_ninja_status_endpoint(self):
        """GET /readspace/v1/status/{pk}/ returns typed status dictionary."""
        with patch("service.selectors.get_article_status", return_value={"id": "art-ninja", "status": "completed"}):
            response = self.client.get("/readspace/v1/status/art-ninja/")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["id"], "art-ninja")
            self.assertEqual(response.json()["status"], "completed")

    def test_ninja_exam_submit_authenticated(self):
        """POST /readspace/v1/{pk}/submit/ validates payload and submits attempt."""
        self.client.login(username="reading_pro", password="SecurePassword123!")

        with (
            patch("service.services.submit_exam_attempt", return_value={"attempt_id": "att-ninja-99"}),
            patch("service.selectors.get_related_articles", return_value=[]),
        ):
            payload = {
                "score": 10.0,
                "total_questions": 10,
                "answers": {"1": "A", "2": "B"},
                "elapsed_time": 200,
            }
            response = self.client.post(
                f"/readspace/v1/{self.article_id}/submit/",
                data=json.dumps(payload),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "success")
            self.assertEqual(data["id"], "att-ninja-99")

    def test_ninja_passage_proof_endpoint(self):
        """GET /readspace/v1/{pk}/proof/{idx}/ returns PassageProofOut."""
        mock_proof = {
            "question_index": 0,
            "question_text": "What are microplastics?",
            "correct_answer": "Plastic particles",
            "proof_found": True,
            "proof_excerpt": "Plastic particles.",
            "confidence_score": 1.0,
        }
        with patch("readspace.api.router.get_passage_proof", return_value=mock_proof):
            response = self.client.get(f"/readspace/v1/{self.article_id}/proof/0/")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["proof"]["proof_excerpt"], "Plastic particles.")

    def test_ninja_openapi_schema_endpoint(self):
        """GET /readspace/v1/openapi.json generates full OpenAPI 3.1 schema."""
        response = self.client.get("/readspace/v1/openapi.json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["info"]["title"], "ReadAndQues REST API")
        self.assertTrue(any("status" in p for p in data["paths"]))
        self.assertTrue(any("submit" in p for p in data["paths"]))
