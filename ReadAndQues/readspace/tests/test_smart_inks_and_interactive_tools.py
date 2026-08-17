"""
ReadAndQues/readspace/tests/test_smart_inks_and_interactive_tools.py
Dedicated functional & integration tests for Readspace Smart Inks,
Highlighting & Marker persistence, Passage Proofs, and AI tools.
"""

import json
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import UserProfile
from service.services import save_user_highlights, smart_paraphrase


class SmartInksAndInteractiveToolsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="smart_ink_scholar",
            email="scholar@example.com",
            password="SecurePassword123!",
        )
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user, defaults={"stars": 15})
        self.article_id = "art_smart_ink_test_01"

    # ── 1. Smart Inks / Smart Paraphrase Service Layer Tests ───────────────────

    def test_smart_paraphrase_service_with_highlighted_text(self):
        """smart_paraphrase invokes LangGraph flow with full initial state."""
        mock_graph_output = {
            "expanded_text": "extreme climate variations",
            "paraphrased_text": "severe weather fluctuations",
            "explanation": "Fluctuations conveys variable patterns.",
            "is_valid": True,
            "retry_count": 1,
        }

        with patch("service.infrastructure.mongo.article_store.find_exact_paraphrase", return_value=None), \
             patch("service.ai_core.graphs.smart_paraphrase.graph.run_smart_paraphrase_flow", return_value=mock_graph_output) as mock_flow, \
             patch("service.infrastructure.mongo.article_store.save_smart_paraphrase", return_value="cache_id_123"):
            
            result = smart_paraphrase(
                article_id=self.article_id,
                paragraph_text="Farmers adapt to extreme climate variations annually.",
                user_start_index=17,
                user_end_index=43,
                highlighted_text="extreme climate variations",
            )

            mock_flow.assert_called_once_with(
                highlighted_text="extreme climate variations",
                paragraph_text="Farmers adapt to extreme climate variations annually.",
                start_idx=17,
                end_idx=43,
            )
            self.assertEqual(result["paraphrased_text"], "severe weather fluctuations")
            self.assertEqual(result["expanded_text"], "extreme climate variations")
            self.assertEqual(result["explanation"], "Fluctuations conveys variable patterns.")

    def test_smart_paraphrase_service_derives_highlight_from_slice(self):
        """When highlighted_text is omitted, smart_paraphrase slices paragraph_text."""
        mock_graph_output = {
            "expanded_text": "marine life",
            "paraphrased_text": "ocean fauna",
            "explanation": "Fauna refers to animals in the ocean.",
        }

        with patch("service.infrastructure.mongo.article_store.find_exact_paraphrase", return_value=None), \
             patch("service.ai_core.graphs.smart_paraphrase.graph.run_smart_paraphrase_flow", return_value=mock_graph_output) as mock_flow, \
             patch("service.infrastructure.mongo.article_store.save_smart_paraphrase", return_value="cache_id_456"):
            
            result = smart_paraphrase(
                article_id=self.article_id,
                paragraph_text="Plastic impacts marine life globally.",
                user_start_index=16,
                user_end_index=27,
            )

            mock_flow.assert_called_once_with(
                highlighted_text="marine life",
                paragraph_text="Plastic impacts marine life globally.",
                start_idx=16,
                end_idx=27,
            )
            self.assertEqual(result["paraphrased_text"], "ocean fauna")

    def test_smart_paraphrase_service_cache_hit_bypasses_llm(self):
        """When paraphrase is already in MongoDB cache, returns cached record immediately."""
        cached_record = {
            "article_id": self.article_id,
            "paragraph_hash": "abc123hash",
            "user_start_index": 0,
            "user_end_index": 10,
            "paraphrased_text": "cached paraphrased string",
            "expanded_text": "cached paraphrased string",
            "explanation": "From cache.",
        }

        with patch("service.infrastructure.mongo.article_store.find_exact_paraphrase", return_value=cached_record), \
             patch("service.ai_core.graphs.smart_paraphrase.graph.run_smart_paraphrase_flow") as mock_flow:
            
            result = smart_paraphrase(
                article_id=self.article_id,
                paragraph_text="Some text",
                user_start_index=0,
                user_end_index=10,
            )

            mock_flow.assert_not_called()
            self.assertEqual(result["paraphrased_text"], "cached paraphrased string")

    def test_smart_paraphrase_service_error_fallback(self):
        """When LLM execution raises an exception, service gracefully falls back without crashing."""
        with patch("service.infrastructure.mongo.article_store.find_exact_paraphrase", return_value=None), \
             patch("service.ai_core.graphs.smart_paraphrase.graph.run_smart_paraphrase_flow", side_effect=RuntimeError("OpenAI 503 Overloaded")):
            
            result = smart_paraphrase(
                article_id=self.article_id,
                paragraph_text="Some paragraph text.",
                highlighted_text="Some paragraph",
                user_start_index=0,
                user_end_index=14,
            )

            self.assertEqual(result["paraphrased_text"], "Some paragraph")
            self.assertIn("Paraphrase service error", result["explanation"])

    # ── 2. Smart Inks HTTP API Endpoint Tests ─────────────────────────────────

    def test_smart_paraphrase_api_http_success(self):
        """POST /readspace/api/<pk>/smart_paraphrase/ returns 200 with paraphrased and expanded text."""
        self.client.login(username="smart_ink_scholar", password="SecurePassword123!")

        mock_result = {
            "article_id": self.article_id,
            "paraphrased_text": "synthetic polymers",
            "expanded_text": "synthetic polymers",
            "explanation": "Technical synonym.",
        }

        with patch("service.services.smart_paraphrase", return_value=mock_result) as mock_service:
            payload = {
                "highlighted_text": "plastics",
                "paragraph_text": "Discarded plastics accumulate in the oceans.",
                "start_index": 10,
                "end_index": 18,
            }
            response = self.client.post(
                reverse("readspace:smart_paraphrase", kwargs={"pk": self.article_id}),
                data=json.dumps(payload),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "success")
            self.assertEqual(data["paraphrased_text"], "synthetic polymers")
            self.assertEqual(data["expanded_text"], "synthetic polymers")
            mock_service.assert_called_once_with(
                article_id=self.article_id,
                paragraph_text="Discarded plastics accumulate in the oceans.",
                user_start_index=10,
                user_end_index=18,
                highlighted_text="plastics",
            )

    def test_smart_paraphrase_api_missing_paragraph_returns_400(self):
        """POST with empty paragraph_text returns 400 bad request."""
        self.client.login(username="smart_ink_scholar", password="SecurePassword123!")

        response = self.client.post(
            reverse("readspace:smart_paraphrase", kwargs={"pk": self.article_id}),
            data=json.dumps({"paragraph_text": "", "highlighted_text": "text"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["status"], "error")

    # ── 3. Highlighter & Marker Saving Persistence Tests ───────────────────────

    def test_save_markers_api_persists_highlights(self):
        """POST /readspace/api/<pk>/save_markers/ persists user highlight markdown."""
        self.client.login(username="smart_ink_scholar", password="SecurePassword123!")

        with patch("service.services.save_user_highlights", return_value=True) as mock_save:
            payload = {"highlighted_markdown": "Passage with ==highlighted phrase== for study."}
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
                highlighted_text="Passage with ==highlighted phrase== for study.",
            )

    # ── 4. Passage Proof Grounding Endpoint Tests ─────────────────────────────

    def test_passage_proof_api_found(self):
        """GET /readspace/<pk>/proof/<idx>/ returns verbatim paragraph proof."""
        mock_proof = {
            "question_index": 0,
            "question_text": "What is the primary factor?",
            "correct_answer": "Climate shifts",
            "proof_found": True,
            "proof_excerpt": "Extreme climate variations are the primary driver.",
            "paragraph_id": "chunk_001",
            "confidence_score": 0.94,
        }

        with patch("service.passage_proof_service.get_passage_proof", return_value=mock_proof):
            response = self.client.get(
                reverse("readspace:passage_proof_api", kwargs={"pk": self.article_id, "idx": 0})
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "success")
            self.assertTrue(data["proof"]["proof_found"])
            self.assertEqual(data["proof"]["confidence_score"], 0.94)

    def test_passage_proof_api_not_found(self):
        """GET /readspace/<pk>/proof/<idx>/ returns 404 when index or article has no proof."""
        with patch("service.passage_proof_service.get_passage_proof", return_value=None):
            response = self.client.get(
                reverse("readspace:passage_proof_api", kwargs={"pk": self.article_id, "idx": 99})
            )
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json()["status"], "error")
