"""
ReadAndQues/service/tests/test_background_tasks.py
Tests for background task dispatcher using Python daemon threads.
"""

from unittest.mock import MagicMock, patch
import threading
from django.test import TestCase

from service.tasks import run_in_background


class BackgroundTaskDispatcherTestCase(TestCase):
    def setUp(self):
        self.article_id = "art-task-test-101"
        self.url = "https://example.com/test-article"

    def test_run_in_background_spawns_daemon_thread(self):
        """Unified background dispatcher executes tasks in daemon threads."""
        mock_func = MagicMock(__name__="mock_task")
        
        thread = run_in_background(mock_func, self.article_id, url=self.url)
        
        self.assertIsInstance(thread, threading.Thread)
        self.assertTrue(thread.daemon)
        thread.join(timeout=2.0)
        mock_func.assert_called_once_with(self.article_id, url=self.url)

    def test_run_in_background_catches_and_logs_exception(self):
        """Background dispatcher handles exceptions without crashing main process."""
        def failing_task():
            raise ValueError("Intentional error for testing")

        thread = run_in_background(failing_task)
        thread.join(timeout=2.0)
        self.assertFalse(thread.is_alive())

