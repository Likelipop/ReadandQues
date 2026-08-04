"""Characterization tests for the legacy Dagster-lite pipeline engine.

These tests intentionally describe current behavior. The typed replacement may
change the public contract later, at which point its tests should replace these
rather than silently changing the assumptions captured here.
"""

from unittest import TestCase

from pipeline.etl.pipeline import Pipe
from pipeline.etl import registry


class RegistryCharacterizationTests(TestCase):
    def setUp(self):
        registry._JOBS.clear()
        registry._PIPES.clear()

    def tearDown(self):
        registry._JOBS.clear()
        registry._PIPES.clear()

    def test_job_decorator_registers_callable_and_metadata(self):
        @registry.job("sum", inputs=["left", "right"], outputs=["total"])
        def add(left, right):
            return left + right

        self.assertIs(registry.get_job("sum"), add)
        self.assertEqual(add.job_inputs, ["left", "right"])
        self.assertEqual(add.job_outputs, ["total"])

    def test_duplicate_job_name_silently_replaces_existing_job(self):
        @registry.job("duplicate")
        def first():
            return "first"

        @registry.job("duplicate")
        def second():
            return "second"

        self.assertIs(registry.get_job("duplicate"), second)
        self.assertIsNot(registry.get_job("duplicate"), first)

    def test_pipe_registers_during_construction(self):
        pipe = Pipe("registered_pipe")

        self.assertIs(registry.get_pipe("registered_pipe"), pipe)

    def test_missing_registry_entries_raise_value_error(self):
        with self.assertRaisesRegex(ValueError, "Job 'missing' not found"):
            registry.get_job("missing")

        with self.assertRaisesRegex(ValueError, "Pipe 'missing' not found"):
            registry.get_pipe("missing")


class PipelineExecutionCharacterizationTests(TestCase):
    def setUp(self):
        registry._JOBS.clear()
        registry._PIPES.clear()

    def tearDown(self):
        registry._JOBS.clear()
        registry._PIPES.clear()

    def test_pipeline_passes_declared_outputs_to_later_jobs(self):
        @registry.job("double", inputs=["value"], outputs=["doubled"])
        def double(value):
            return value * 2

        @registry.job("describe", inputs=["doubled"], outputs=["description"])
        def describe(doubled):
            return {"description": f"value={doubled}"}

        result = Pipe("flow").add_job("double").add_job("describe").invoke(value=3)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["context"]["doubled"], 6)
        self.assertEqual(result["context"]["description"], "value=6")
        self.assertEqual(result["results"]["double"], 6)

    def test_pipeline_unpacks_tuple_outputs(self):
        @registry.job("split", outputs=["left", "right"])
        def split(**_context):
            return "a", "b"

        result = Pipe("tuple_flow").add_job("split").invoke()

        self.assertEqual(result["context"]["left"], "a")
        self.assertEqual(result["context"]["right"], "b")

    def test_job_without_declared_outputs_merges_dictionary_result(self):
        @registry.job("legacy_merge")
        def legacy_merge(**_context):
            return {"legacy_value": 42}

        result = Pipe("legacy_flow").add_job("legacy_merge").invoke()

        self.assertEqual(result["context"]["legacy_value"], 42)

    def test_missing_required_context_is_reported_as_failed_result(self):
        @registry.job("requires_value", inputs=["value"], outputs=["result"])
        def requires_value(value):
            return value

        result = Pipe("missing_input_flow").add_job("requires_value").invoke()

        self.assertEqual(result["status"], "failed")
        self.assertIn("requires_value", result["results"])
        self.assertIn("error", result["results"]["requires_value"])

    def test_pipeline_stops_after_first_raised_exception(self):
        calls = []

        @registry.job("explode")
        def explode(**_context):
            calls.append("explode")
            raise RuntimeError("boom")

        @registry.job("must_not_run")
        def must_not_run(**_context):
            calls.append("must_not_run")

        result = Pipe("failing_flow").add_job("explode").add_job("must_not_run").invoke()

        self.assertEqual(result["status"], "failed")
        self.assertEqual(calls, ["explode"])
        self.assertNotIn("must_not_run", result["results"])
