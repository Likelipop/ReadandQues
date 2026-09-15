"""
ReadAndQues/readspace/tests/test_api_contracts.py
Comprehensive tests for API Contract verification, parameter alias compatibility,
and payload validation between frontend and backend services.
"""

import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse


class APIContractsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="contract_user",
            email="contract@example.com",
            password="SecurePassword123!",
        )
        self.article_id = "art-contract-001"

    # ── 1. save_markers Contract Tests ──────────────────────────────────────────

    def test_save_markers_with_highlighted_markdown_key(self):
        """save_markers accepts 'highlighted_markdown' and calls save_user_highlights."""
        self.client.login(username="contract_user", password="SecurePassword123!")

        with patch("service.services.save_user_highlights", return_value=True) as mock_save:
            response = self.client.post(
                reverse("readspace:save_markers", kwargs={"pk": self.article_id}),
                data=json.dumps({"highlighted_markdown": "==Important Note=="}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["status"], "success")
            mock_save.assert_called_once_with(
                user_id=self.user.id,
                article_id=self.article_id,
                highlighted_text="==Important Note==",
            )

    def test_save_markers_with_legacy_highlights_key(self):
        """save_markers accepts legacy 'highlights' key and maps to highlighted_text."""
        self.client.login(username="contract_user", password="SecurePassword123!")

        with patch("service.services.save_user_highlights", return_value=True) as mock_save:
            response = self.client.post(
                reverse("readspace:save_markers", kwargs={"pk": self.article_id}),
                data=json.dumps({"highlights": "==Legacy Highlight=="}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
            mock_save.assert_called_once_with(
                user_id=self.user.id,
                article_id=self.article_id,
                highlighted_text="==Legacy Highlight==",
            )

    def test_ninja_save_markers_endpoint_contract(self):
        """Django Ninja save_markers endpoint correctly passes highlighted_text without TypeError."""
        self.client.login(username="contract_user", password="SecurePassword123!")

        with patch("service.services.save_user_highlights", return_value=True) as mock_save:
            response = self.client.post(
                f"/readspace/v1/{self.article_id}/save_markers/",
                data=json.dumps({"highlighted_markdown": "==Ninja Highlight=="}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
            mock_save.assert_called_once_with(
                user_id=self.user.id,
                article_id=self.article_id,
                highlighted_text="==Ninja Highlight==",
            )

    # ── 3. submit_exam_attempt Contract Tests ───────────────────────────────────

    def test_submit_exam_with_elapsed_time_and_time_taken_seconds(self):
        """submit_exam_attempt parses elapsed_time and falls back to time_taken_seconds."""
        self.client.login(username="contract_user", password="SecurePassword123!")

        with (
            patch("service.services.submit_exam_attempt", return_value={"attempt_id": "att-1"}) as mock_submit,
            patch("service.selectors.get_related_articles", return_value=[]),
        ):
            # Test time_taken_seconds alias
            payload = {
                "score": 8,
                "total_questions": 10,
                "answers": {"1": "A"},
                "time_taken_seconds": 240,
            }
            response = self.client.post(
                reverse("readspace:submit_exam_attempt", kwargs={"pk": self.article_id}),
                data=json.dumps(payload),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
            mock_submit.assert_called_once_with(
                user_id=self.user.id,
                article_id=self.article_id,
                score=8,
                total_questions=10,
                answers={"1": "A"},
                highlighted_markdown="",
                elapsed_time=240,
            )


    # ── 5. Ninja REST API Discovery & Auth Endpoints ─────────────────────────

    def test_homepage_bundle_api(self):
        """GET /api/v1/homepage/ returns status success and complete structure."""
        response = self.client.get("/api/v1/homepage/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("hero_articles", data)
        self.assertIn("daily_vocab", data)
        self.assertIn("themes", data)

    def test_articles_list_api(self):
        """GET /api/v1/articles/ returns paginated list."""
        response = self.client.get("/api/v1/articles/?theme=All&page=1&limit=6")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("articles", data)
        self.assertIn("total_count", data)

    def test_auth_me_api(self):
        """GET /api/v1/auth/me/ returns authenticated user data when logged in."""
        self.client.login(username="contract_user", password="SecurePassword123!")
        response = self.client.get("/api/v1/auth/me/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["is_authenticated"])
        self.assertEqual(data["username"], "contract_user")

    def test_auth_login_and_logout_api(self):
        """POST /api/v1/auth/login/ and /api/v1/auth/logout/ manage session."""
        login_res = self.client.post(
            "/api/v1/auth/login/",
            data=json.dumps({"username": "contract_user", "password": "SecurePassword123!"}),
            content_type="application/json",
        )
        self.assertEqual(login_res.status_code, 200)
        self.assertEqual(login_res.json()["status"], "success")

        logout_res = self.client.post("/api/v1/auth/logout/")
        self.assertEqual(logout_res.status_code, 200)
        self.assertEqual(logout_res.json()["status"], "success")
