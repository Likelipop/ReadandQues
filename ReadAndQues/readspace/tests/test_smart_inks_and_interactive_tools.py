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
from service.services import save_user_highlights


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

        with patch("ai_service.rag.grounding.get_passage_proof", return_value=mock_proof):
            response = self.client.get(reverse("readspace:passage_proof_api", kwargs={"pk": self.article_id, "idx": 0}))
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "success")
            self.assertTrue(data["proof"]["proof_found"])
            self.assertEqual(data["proof"]["confidence_score"], 0.94)

    def test_passage_proof_api_not_found(self):
        """GET /readspace/<pk>/proof/<idx>/ returns 404 when index or article has no proof."""
        with patch("ai_service.rag.grounding.get_passage_proof", return_value=None):
            response = self.client.get(
                reverse("readspace:passage_proof_api", kwargs={"pk": self.article_id, "idx": 99})
            )
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json()["status"], "error")
