"""
ReadAndQues/service/tests/test_celery_pipeline_functional.py
Functional tests for Celery task definitions, execution dispatching, and fallback mechanisms.
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from service.tasks import (
    run_in_background,
    task_enrich_article_only,
    task_ingest_and_enrich_article,
    task_rebuild_bm25_index,
)


class CeleryPipelineFunctionalTestCase(TestCase):
    def setUp(self):
        self.article_id = "art-task-test-101"
        self.url = "https://example.com/test-article"

    def test_task_enrich_article_only_execution(self):
        """Celery enrich task executes pipeline and returns result dictionary."""
        mock_output = {"status": "success", "article_id": self.article_id, "questions_count": 5}
        with patch("service.pipelines.enrich_article_only", return_value=mock_output) as mock_pipeline:
            result = task_enrich_article_only(self.article_id)
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["article_id"], self.article_id)
            mock_pipeline.assert_called_once_with(article_id=self.article_id)

    def test_task_ingest_and_enrich_article_execution(self):
        """Celery ingest task coordinates web scraping and quiz generation."""
        mock_output = {"status": "success", "article_id": self.article_id, "title": "Scraped Article"}
        with patch("service.pipelines.ingest_and_enrich_article", return_value=mock_output) as mock_pipeline:
            result = task_ingest_and_enrich_article(self.article_id, self.url)
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["title"], "Scraped Article")
            mock_pipeline.assert_called_once_with(article_id=self.article_id, url=self.url)

    def test_task_rebuild_bm25_index_execution(self):
        """Celery BM25 task calls rebuild_index on connection."""
        with patch("service.infrastructure.bm25.connection.rebuild_index") as mock_rebuild:
            task_rebuild_bm25_index()
            mock_rebuild.assert_called_once()

    def test_run_in_background_dispatches_to_celery_when_available(self):
        """Unified background dispatcher routes to Celery .delay() when callable."""
        from service.pipelines import enrich_article_only

        with patch("service.tasks.task_enrich_article_only.delay") as mock_delay:
            mock_delay.return_value = MagicMock(id="task-celery-123")
            result = run_in_background(enrich_article_only, article_id=self.article_id)
            mock_delay.assert_called_once_with(article_id=self.article_id)
            self.assertEqual(result.id, "task-celery-123")

    def test_run_in_background_falls_back_to_thread_on_celery_error(self):
        """Unified background dispatcher falls back to thread when Celery broker is unavailable."""
        from service.pipelines import enrich_article_only

        with patch("service.tasks.task_enrich_article_only.delay", side_effect=Exception("Redis connection refused")), \
             patch("threading.Thread.start") as mock_thread_start:
            result = run_in_background(enrich_article_only, article_id=self.article_id)
            self.assertIsNotNone(result)
            mock_thread_start.assert_called_once()
