"""
Unit & Integration tests for readspace views and Ninja API endpoints.
"""

import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse


class ReadspaceViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpassword123",
        )

    def test_readspace_requires_login(self):
        response = self.client.get(reverse("readspace:readspace_detail", kwargs={"pk": "article-123"}))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_all_tests_view_accessible_unauthenticated(self):
        with (
            patch("service.selectors.list_completed_articles", return_value={"articles": []}),
            patch("service.selectors.get_theme_choices", return_value=[]),
            patch("service.selectors.get_genre_choices", return_value=[]),
            patch("service.selectors.get_user_attempted_ids", return_value=set()),
        ):
            response = self.client.get(reverse("readspace:all_tests"))
            self.assertEqual(response.status_code, 200)

    def test_submit_exam_attempt_unauthenticated_forbidden_or_redirect(self):
        response = self.client.post(
            reverse("readspace:submit_exam_attempt", kwargs={"pk": "article-123"}),
            data=json.dumps({"score": 5, "total_questions": 10}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 302)

    def test_submit_exam_attempt_authenticated_success(self):
        self.client.login(username="testuser", password="testpassword123")
        with (
            patch("service.services.submit_exam_attempt", return_value={"attempt_id": "attempt-456"}),
            patch("service.selectors.get_related_articles", return_value=[]),
        ):
            response = self.client.post(
                reverse("readspace:submit_exam_attempt", kwargs={"pk": "article-123"}),
                data=json.dumps(
                    {
                        "score": 8,
                        "total_questions": 10,
                        "answers": {"1": "TRUE"},
                        "elapsed_time": 120,
                    }
                ),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "success")
            self.assertEqual(data["id"], "attempt-456")

    def test_passage_proof_api_not_found(self):
        with patch("service.ai_core.grounding.get_passage_proof", return_value=None):
            response = self.client.get(reverse("readspace:passage_proof_api", kwargs={"pk": "article-1", "idx": 0}))
            self.assertEqual(response.status_code, 404)

    def test_ninja_api_status_endpoint(self):
        with patch("service.selectors.get_article_status", return_value={"id": "art-1", "status": "completed"}):
            response = self.client.get("/readspace/v1/status/art-1/")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["id"], "art-1")
