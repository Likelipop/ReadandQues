"""
ReadAndQues/readspace/tests/test_ai_auth_guard.py
Tests verifying that all AI-powered endpoints require authentication (HTTP 401)
while ReadSpace reading, dictionary lookups, and guest practice submissions remain open.
"""

import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse


class AIAuthGuardTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="ai_user",
            email="ai_user@example.com",
            password="TestPassword123!",
        )
        self.article_id = "test-art-guard-001"

    # ── 1. Unauthenticated / Guest Access to AI Endpoints (Must Return 401) ─────

    def test_unauthenticated_study_dock_stream_returns_401(self):
        """Guests cannot access SSE study dock streaming without authentication."""
        response = self.client.post(
            reverse("readspace:study_dock_stream"),
            data=json.dumps({"query": "Hello", "article_id": self.article_id}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertEqual(data["status"], "error")
        self.assertIn("Authentication required", data["message"])

    def test_unauthenticated_explain_stream_returns_401(self):
        """Guests cannot access sentence/phrase explain streaming without authentication."""
        response = self.client.post(
            reverse("readspace:explain_stream_api"),
            data=json.dumps({"phrase": "mitigate emissions"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertEqual(data["status"], "error")
        self.assertIn("Authentication required", data["message"])




    def test_unauthenticated_trigger_quiz_view_returns_401(self):
        """Guests cannot trigger AI quiz generation via Django view."""
        response = self.client.post(
            reverse("readspace:trigger_quiz", kwargs={"pk": self.article_id}),
        )
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertEqual(data["status"], "error")
        self.assertIn("Authentication required", data["message"])

    def test_unauthenticated_ninja_trigger_quiz_returns_401(self):
        """Django Ninja POST /api/v1/trigger-quiz/{pk}/ returns 401 for guests."""
        response = self.client.post(f"/api/v1/trigger-quiz/{self.article_id}/")
        self.assertEqual(response.status_code, 401)

    def test_unauthenticated_ninja_explain_phrase_returns_401(self):
        """Django Ninja POST /api/v1/{pk}/explain/ returns 401 for guests."""
        response = self.client.post(
            f"/api/v1/{self.article_id}/explain/",
            data=json.dumps({"phrase": "quantum entanglement"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_unauthenticated_ninja_import_article_returns_401(self):
        """Django Ninja POST /api/v1/articles/import/ returns 401 for guests."""
        response = self.client.post(
            "/api/v1/articles/import/",
            data=json.dumps({"url": "https://example.com/news-story"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    # ── 2. Guest / Unauthenticated Access to ReadSpace (Must be 200 OK) ──────────

    def test_guest_can_list_articles_in_readspace(self):
        """Unauthenticated guests can freely browse article list."""
        response = self.client.get("/api/v1/articles/")
        self.assertEqual(response.status_code, 200)

    def test_guest_can_access_dictionary_lookup(self):
        """Unauthenticated guests can freely look up definitions with offline WordNet."""
        response = self.client.get("/api/v1/dictionary/lookup/?word=mitigate")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["word"], "mitigate")
        self.assertTrue(data["found"])

    def test_guest_can_submit_practice_exam(self):
        """Unauthenticated guests can submit answers for practice without being blocked."""
        with (
            patch("service.services.submit_exam_attempt", return_value={"attempt_id": "guest-att-1"}),
            patch("service.selectors.get_related_articles", return_value=[]),
        ):
            payload = {
                "score": 5,
                "total_questions": 5,
                "answers": {"0": "A"},
                "time_taken_seconds": 120,
            }
            response = self.client.post(
                f"/api/v1/{self.article_id}/submit/",
                data=json.dumps(payload),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)

    # ── 3. Authenticated Access to AI Endpoints (Must Succeed) ───────────────────

    def test_authenticated_user_can_access_study_dock_stream(self):
        """Authenticated users can successfully initiate study dock SSE streaming."""
        self.client.login(username="ai_user", password="TestPassword123!")

        with patch("ai_service.interface.stream_study_dock_sync") as mock_stream:
            mock_stream.return_value = iter([
                {"type": "metadata", "intent": "rag", "citations": []},
                {"type": "delta", "text": "AI response chunk"},
                {"type": "done"},
            ])
            response = self.client.post(
                reverse("readspace:study_dock_stream"),
                data=json.dumps({"query": "Explain concept", "article_id": self.article_id}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Type"], "text/event-stream")

    def test_authenticated_user_can_trigger_quiz(self):
        """Authenticated users can trigger AI quiz generation."""
        self.client.login(username="ai_user", password="TestPassword123!")

        with patch("service.services.trigger_quiz_generation", return_value={"status": "processing"}):
            response = self.client.post(
                f"/api/v1/trigger-quiz/{self.article_id}/",
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["status"], "processing")
