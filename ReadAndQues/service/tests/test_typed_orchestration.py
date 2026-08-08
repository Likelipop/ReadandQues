from unittest import TestCase
from unittest.mock import Mock, patch

from service.orchestration.configuration import Pipe
from service.orchestration.configuration import registry
from service.orchestration.contracts import JobResult, PipelineContext, PipelineResult
from service.orchestration.exceptions import (
    JobFailedError,
    MissingContextError,
    OrchestrationError,
    PipelineValidationError,
)
from service.orchestration.executors import InlineExecutor, ThreadedBackgroundExecutor
from service.orchestration.pipes import (
    bronze_to_silver_pipe,
    ingest_bronze_pipe,
    init_pipe,
    silver_to_gold_pipe,
    single_article_pipe,
    smart_ink_pipe,
)
from service.orchestrator import OrchestrationFacade


class TypedOrchestrationTests(TestCase):
    def setUp(self):
        registry._JOBS.clear()
        registry._PIPES.clear()

    def tearDown(self):
        registry._JOBS.clear()
        registry._PIPES.clear()

    def test_pipeline_context_set_get_to_dict(self):
        ctx = PipelineContext()
        ctx.set("key1", "val1")
        ctx.update({"key2": 123})
        self.assertEqual(ctx.get("key1"), "val1")
        self.assertEqual(ctx.get("key2"), 123)
        self.assertTrue(ctx.contains("key1"))
        self.assertFalse(ctx.contains("key3"))
        self.assertEqual(ctx.to_dict(), {"key1": "val1", "key2": 123})

    def test_job_and_pipeline_result_contracts(self):
        job_res = JobResult(job_name="test_job", status="completed", output={"x": 1})
        self.assertEqual(job_res.job_name, "test_job")
        self.assertEqual(job_res.status, "completed")

        pipe_res = PipelineResult(
            pipeline_name="test_pipe",
            status="completed",
            results={"test_job": job_res},
            context={"x": 1},
        )
        self.assertEqual(pipe_res.pipeline_name, "test_pipe")
        self.assertEqual(pipe_res.status, "completed")

    def test_inline_executor(self):
        @registry.job("dummy_job", inputs=["val"], outputs=["result"])
        def dummy_job(val):
            return {"result": val * 2}

        pipe = Pipe("dummy_pipe").add_job("dummy_job")
        res = InlineExecutor.execute(pipe, val=5)
        self.assertEqual(res["status"], "completed")
        self.assertEqual(res["context"]["result"], 10)

    def test_threaded_background_executor(self):
        @registry.job("async_job", inputs=["msg"], outputs=["reply"])
        def async_job(msg):
            return {"reply": f"echo: {msg}"}

        pipe = Pipe("async_pipe").add_job("async_job")
        callback_called = False

        def callback(res):
            nonlocal callback_called
            callback_called = True

        thread = ThreadedBackgroundExecutor.submit(pipe, callback=callback, msg="hello")
        thread.join(timeout=2.0)
        self.assertTrue(callback_called)

    def test_truthful_failure_reporting_in_daily_pipeline(self):
        with patch("service.orchestrator.get_pipe") as mock_get_pipe:
            failed_pipe = Mock()
            failed_pipe.invoke.return_value = {
                "status": "failed",
                "results": {"ingest_to_bronze": {"status": "failed", "error": "Network timeout"}},
            }
            mock_get_pipe.return_value = failed_pipe

            result = OrchestrationFacade.run_daily_pipeline()
            self.assertEqual(result["status"], "failed")
            self.assertIn("Daily pipeline failed at stage", result["message"])

    def test_no_one_job_query_pipelines_exist_in_registry(self):
        from service.orchestration import pipes  # noqa: F401
        obsolete_query_pipes = [
            "get_article_by_id_pipe",
            "get_completed_articles_pipe",
            "get_user_attempted_ids_pipe",
            "save_exam_attempt_pipe",
            "find_related_by_markers_pipe",
        ]
        for pipe_name in obsolete_query_pipes:
            with self.assertRaises(ValueError):
                registry.get_pipe(pipe_name)
