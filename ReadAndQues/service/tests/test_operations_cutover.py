import os
from unittest import TestCase
from unittest.mock import Mock, patch

import django
from django.conf import settings

if not settings.configured:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ReadAndQues.settings")
    django.setup()

from service.domain.contracts import ExamAttemptContract
from service.models import ArticleImportRequest, ExamAttemptLog
from service.repositories.attempt_repository import AttemptRepository


class OperationsCutoverTests(TestCase):
    def test_article_import_request_creation(self):
        req = ArticleImportRequest(
            request_id="req_123",
            user_id=1,
            url="https://example.com/import",
            stars_charged=1,
        )
        self.assertEqual(req.user_id, 1)
        self.assertEqual(req.stars_charged, 1)

    def test_exam_attempt_log_model(self):
        attempt = ExamAttemptLog(
            attempt_id="att_123",
            user_id=1,
            article_id="art_456",
            score=8,
            total_questions=10,
        )
        self.assertEqual(attempt.score, 8)
        self.assertEqual(attempt.article_id, "art_456")

    def test_attempt_repository_save(self):
        repo = AttemptRepository()
        contract = ExamAttemptContract(
            user_id=1,
            article_id="art_100",
            score=5,
            total_questions=5,
        )
        with patch.object(repo.coll, "insert_one") as mock_insert:
            mock_insert.return_value = Mock(inserted_id="507f1f77bcf86cd799439011")
            inserted = repo.save_attempt(contract)
            self.assertEqual(inserted, "507f1f77bcf86cd799439011")
