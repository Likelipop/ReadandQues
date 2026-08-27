"""
ReadAndQues/readspace/tests/test_readspace_live_regression.py
Exhaustive regression test suite testing all article state variations, exam payload types,
missing data resiliency, and edge cases to ensure zero 500 errors across /readspace/.
"""

import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import UserProfile
from service.selectors import (
    get_article_detail,
    get_article_status,
    get_related_articles,
    list_completed_articles,
)


class ReadspaceLiveRegressionTestSuite(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="student_reader",
            email="student@example.com",
            password="SecurePassword123!",
        )
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user, defaults={"stars": 10})
        self.article_id = "art_814473a610b4ab5d"

        self.mock_mongo_index_doc = {
            "_id": self.article_id,
            "url": "https://www.bbc.com/news/articles/c207559e8x3o",
            "title": "Global Agricultural Shifts in 2026",
            "source_name": "BBC News",
            "image_url": "https://example.com/banner.jpg",
            "published_at": "2026-08-15T12:00:00Z",
            "stage": "gold",
            "ai_status": "completed",
            "error_message": "",
        }

        self.mock_minio_clean_doc = {
            "article_id": self.article_id,
            "title": "Global Agricultural Shifts in 2026",
            "original_text": "Farmers worldwide are adapting to extreme climate variations [1] through modern tech [2].",
            "cleaned_text": "Farmers worldwide are adapting to extreme climate variations [1] through modern tech [2].",
            "html_content": "<p>Farmers worldwide are adapting to extreme climate variations [1] through modern tech [2].</p>",
            "word_count": 150,
            "language": "en",
        }

        # Multi-type IELTS Exam Payload (Multiple Choice + YNNG + FIB)
        self.mock_mongo_exam_doc = {
            "article_id": self.article_id,
            "theme": "Environment",
            "genre": "scientific",
            "summary": "Report on farming resilience against climate shifts.",
            "exams": [
                {
                    "exam_id": "exam_001",
                    "title": "IELTS Academic Reading Practice",
                    "quizzes": [
                        {
                            "quiz_type": "multiple_choice",
                            "question": "What is the main challenge faced by farmers?",
                            "options": [
                                "Extreme climate variations",
                                "Labor shortages",
                                "Urban expansion",
                                "Fertilizer costs",
                            ],
                            "correct_answer": "Extreme climate variations",
                            "explanation": "Paragraph 1 explicitly mentions climate variations.",
                            "supporting_text": "Farmers worldwide are adapting to extreme climate variations.",
                            "source_chunk_ids": ["chunk_001"],
                        },
                        {
                            "quiz_type": "yes_no_notgiven",
                            "question": "All agricultural regions are equally affected.",
                            "options": ["YES", "NO", "NOT GIVEN"],
                            "correct_answer": "NO",
                            "explanation": "The report highlights varied regional impacts.",
                            "supporting_text": "Impacts vary widely by geographic zone.",
                        },
                        {
                            "quiz_type": "fill_in_blank",
                            "question": "Farmers adapt using [1] and new methods [2].",
                            "options": [],
                            "correct_answer": "modern technology",
                            "explanation": "Stated in paragraph 2.",
                            "supporting_text": "Adapting through modern tech.",
                        },
                    ],
                }
            ],
            "analysis": {
                "genre": "scientific",
                "theme": "Environment",
                "core": {
                    "summary": "Report on farming resilience against climate shifts.",
                },
            },
        }

    # ── 1. get_article_detail Resiliency Tests ─────────────────────────────────

    def test_get_article_detail_full_payload(self):
        """Successfully parses all IELTS question types (MCQ, YNNG, FIB) into Article."""
        with (
            patch(
                "service.infrastructure.mongo.article_store.get_article_index", return_value=self.mock_mongo_index_doc
            ),
            patch(
                "service.infrastructure.minio.object_store.read_silver_clean", return_value=self.mock_minio_clean_doc
            ),
            patch("service.infrastructure.mongo.exam_store.get_exam", return_value=self.mock_mongo_exam_doc),
        ):
            detail = get_article_detail(self.article_id)
            self.assertIsNotNone(detail)
            self.assertEqual(detail["article_id"], self.article_id)
            self.assertEqual(len(detail["exams"][0]["quizzes"]), 3)
            self.assertEqual(detail["exams"][0]["quizzes"][0]["quiz_type"], "multiple_choice")
            self.assertEqual(detail["exams"][0]["quizzes"][1]["quiz_type"], "yes_no_notgiven")
            self.assertEqual(detail["exams"][0]["quizzes"][2]["quiz_type"], "fill_in_blank")

    def test_get_article_detail_when_minio_or_exam_is_none(self):
        """Handles missing MinIO silver object and missing MongoDB exam without exception."""
        with (
            patch(
                "service.infrastructure.mongo.article_store.get_article_index", return_value=self.mock_mongo_index_doc
            ),
            patch("service.infrastructure.minio.object_store.read_silver_clean", return_value=None),
            patch("service.infrastructure.mongo.exam_store.get_exam", return_value=None),
        ):
            detail = get_article_detail(self.article_id)
            self.assertIsNotNone(detail)
            self.assertEqual(detail["has_quiz"], False)
            self.assertEqual(detail["exams"], [])
            self.assertEqual(detail["original_text"], "")

    def test_get_article_detail_when_index_not_found(self):
        """Returns None if article_id does not exist in article_index."""
        with patch("service.infrastructure.mongo.article_store.get_article_index", return_value=None):
            detail = get_article_detail("non_existent_id")
            self.assertIsNone(detail)

    # ── 2. readspace_view (GET /readspace/<pk>/) HTTP Tests ────────────────────

    def test_readspace_view_authenticated_full_render(self):
        """Logged in user GET /readspace/<pk>/ returns 200 and renders HTML templates cleanly."""
        self.client.login(username="student_reader", password="SecurePassword123!")

        with (
            patch(
                "service.infrastructure.mongo.article_store.get_article_index", return_value=self.mock_mongo_index_doc
            ),
            patch(
                "service.infrastructure.minio.object_store.read_silver_clean", return_value=self.mock_minio_clean_doc
            ),
            patch("service.infrastructure.mongo.exam_store.get_exam", return_value=self.mock_mongo_exam_doc),
            patch("service.infrastructure.mongo.article_store.list_completed_articles", return_value=[]),
            patch("service.infrastructure.mongo.exam_store.get_exams_by_article_ids", return_value={}),
        ):
            response = self.client.get(f"/readspace/{self.article_id}/")
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Global Agricultural Shifts in 2026")
            self.assertContains(response, "What is the main challenge faced by farmers?")
            self.assertContains(response, "Yes / No / Not Given")
            self.assertContains(response, "Summary Completion")

    def test_readspace_view_redirects_when_article_not_found(self):
        """GET /readspace/<invalid_id>/ sets error message and redirects to home."""
        self.client.login(username="student_reader", password="SecurePassword123!")

        with patch("service.infrastructure.mongo.article_store.get_article_index", return_value=None):
            response = self.client.get("/readspace/art_not_found/")
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, "/")

    def test_readspace_view_redirects_anonymous_to_login(self):
        """Anonymous GET /readspace/<pk>/ redirects to /login/."""
        response = self.client.get(f"/readspace/{self.article_id}/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    # ── 3. Article Status Polling & Related Articles Resiliency ────────────────

    def test_get_article_status_in_progress(self):
        """Status polling for in-progress article returns status payload."""
        pending_index_doc = {**self.mock_mongo_index_doc, "ai_status": "processing"}
        with (
            patch("service.infrastructure.mongo.article_store.get_article_index", return_value=pending_index_doc),
            patch("service.infrastructure.mongo.exam_store.get_exam", return_value=None),
        ):
            status_data = get_article_status(self.article_id)
            self.assertEqual(status_data["status"], "processing")
            self.assertEqual(status_data["has_quiz"], False)
            self.assertEqual(status_data["exams"], [])

    def test_get_article_status_failed_error(self):
        """Status polling for failed article returns error message without crash."""
        error_index_doc = {
            **self.mock_mongo_index_doc,
            "ai_status": "failed",
            "error_message": "Upstream LLM timeout",
        }
        with (
            patch("service.infrastructure.mongo.article_store.get_article_index", return_value=error_index_doc),
            patch("service.infrastructure.mongo.exam_store.get_exam", return_value=None),
        ):
            status_data = get_article_status(self.article_id)
            self.assertEqual(status_data["status"], "failed")
            self.assertEqual(status_data["error_message"], "Upstream LLM timeout")

    def test_get_related_articles_filters_current_id(self):
        """get_related_articles excludes the current article_id and returns recommendations."""
        mock_completed_indexes = [
            {"_id": self.article_id, "title": "Current Article", "url": "https://a.com"},
            {"_id": "art_other_001", "title": "Other Article 1", "url": "https://b.com"},
            {"_id": "art_other_002", "title": "Other Article 2", "url": "https://c.com"},
        ]
        with (
            patch(
                "service.infrastructure.mongo.article_store.list_completed_articles",
                return_value=mock_completed_indexes,
            ),
            patch("service.infrastructure.mongo.exam_store.get_exams_by_article_ids", return_value={}),
        ):
            related = get_related_articles(self.article_id, limit=3)
            self.assertEqual(len(related), 2)
            for r in related:
                self.assertNotEqual(r["article_id"], self.article_id)
