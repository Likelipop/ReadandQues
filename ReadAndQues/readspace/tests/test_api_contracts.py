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

    # ── 2. smart_paraphrase Contract Tests ─────────────────────────────────────

    def test_smart_paraphrase_with_start_index_end_index(self):
        """smart_paraphrase accepts 'start_index' / 'end_index' and returns expanded_text alias."""
        self.client.login(username="contract_user", password="SecurePassword123!")

        mock_result = {
            "paraphrased_text": "Paraphrased version.",
            "explanation": "Simplified sentence.",
        }

        with patch("service.services.smart_paraphrase", return_value=mock_result) as mock_para:
            payload = {
                "paragraph_text": "Original text passage.",
                "start_index": 5,
                "end_index": 15,
            }
            response = self.client.post(
                reverse("readspace:smart_paraphrase", kwargs={"pk": self.article_id}),
                data=json.dumps(payload),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["paraphrased_text"], "Paraphrased version.")
            self.assertEqual(data["expanded_text"], "Paraphrased version.")
            mock_para.assert_called_once_with(
                article_id=self.article_id,
                paragraph_text="Original text passage.",
                user_start_index=5,
                user_end_index=15,
                highlighted_text="",
            )

    def test_smart_paraphrase_with_start_idx_end_idx(self):
        """smart_paraphrase accepts 'start_idx' / 'end_idx' shorthand."""
        self.client.login(username="contract_user", password="SecurePassword123!")

        with patch("service.services.smart_paraphrase", return_value={"paraphrased_text": "P"}) as mock_para:
            payload = {
                "paragraph_text": "Sample text.",
                "start_idx": 2,
                "end_idx": 8,
            }
            response = self.client.post(
                reverse("readspace:smart_paraphrase", kwargs={"pk": self.article_id}),
                data=json.dumps(payload),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
            mock_para.assert_called_once_with(
                article_id=self.article_id,
                paragraph_text="Sample text.",
                user_start_index=2,
                user_end_index=8,
                highlighted_text="",
            )

    # ── 3. submit_exam_attempt Contract Tests ───────────────────────────────────

    def test_submit_exam_with_elapsed_time_and_time_taken_seconds(self):
        """submit_exam_attempt parses elapsed_time and falls back to time_taken_seconds."""
        self.client.login(username="contract_user", password="SecurePassword123!")

        with patch("service.services.submit_exam_attempt", return_value={"attempt_id": "att-1"}) as mock_submit, \
             patch("service.selectors.get_related_articles", return_value=[]):
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

    # ── 4. run_ai_tool_api / Ask AI Tickets Contract Tests ─────────────────────

    def test_run_ai_tool_handles_legacy_input_data_and_normalized_output(self):
        """run_ai_tool_api parses input_data.question and returns output.status='RESOLVED'."""
        self.client.login(username="contract_user", password="SecurePassword123!")

        mock_rag_response = {
            "status": "success",
            "answer": "The main conclusion is carbon reduction.",
            "citations": [{"source": "Para 1", "quote": "Carbon emissions must decline."}],
        }

        with patch("service.services.ask_rag_question", return_value=mock_rag_response) as mock_rag:
            payload = {
                "tool_name": "ask_article",
                "article_id": self.article_id,
                "input_data": {
                    "question": "What is the conclusion?",
                    "article_text": "Sample passage...",
                },
            }
            response = self.client.post(
                reverse("readspace:run_ai_tool_api"),
                data=json.dumps(payload),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "success")
            self.assertEqual(data["answer"], "The main conclusion is carbon reduction.")
            self.assertIn("output", data)
            self.assertEqual(data["output"]["status"], "RESOLVED")
            self.assertEqual(data["output"]["answer"], "The main conclusion is carbon reduction.")
            self.assertEqual(data["output"]["citation_quote"], "Carbon emissions must decline.")
            mock_rag.assert_called_once_with(
                question="What is the conclusion?",
                article_id=self.article_id,
            )
