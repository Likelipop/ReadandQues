"""Characterization tests for the legacy article and AI workflow functions.

The legacy jobs package eagerly imports every infrastructure adapter. Loading the
target modules with explicit doubles both avoids live services and documents the
coupling that the application-service refactor must remove.
"""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from unittest import TestCase
from unittest.mock import Mock, patch


PIPELINE_DIR = Path(__file__).resolve().parents[1]


def dependency(name, **attributes):
    module = ModuleType(name)
    for attribute, value in attributes.items():
        setattr(module, attribute, value)
    return module


def load_legacy_module(module_name, relative_path, dependencies):
    path = PIPELINE_DIR / relative_path
    spec = spec_from_file_location(module_name, path)
    module = module_from_spec(spec)
    with patch.dict("sys.modules", dependencies):
        spec.loader.exec_module(module)
    return module


class SingleArticleWorkflowCharacterizationTests(TestCase):
    def build_module(self):
        self.clean = Mock()
        self.add_vector = Mock()
        self.crawl = Mock()
        self.update_article = Mock(return_value=True)
        self.run_ai = Mock()

        dependencies = {
            "pipeline.etl.jobs.clean_logic": dependency(
                "pipeline.etl.jobs.clean_logic",
                clean_and_validate_article=self.clean,
            ),
            "database.Chroma.operations": dependency(
                "database.Chroma.operations", add_article_vector=self.add_vector
            ),
            "database.Crawler.scraper": dependency(
                "database.Crawler.scraper", crawl_article_content=self.crawl
            ),
            "database.Mongo.crud": dependency(
                "database.Mongo.crud", update_article_document=self.update_article
            ),
            "pipeline.etl.jobs.generate_questions": dependency(
                "pipeline.etl.jobs.generate_questions", run_ai_pipeline=self.run_ai
            ),
        }
        return load_legacy_module(
            "legacy_single_article_for_test",
            "etl/jobs/single_article.py",
            dependencies,
        )

    def test_successful_workflow_crawls_cleans_generates_persists_and_indexes(self):
        module = self.build_module()
        self.crawl.return_value = {"success": True, "raw_text": "raw"}
        self.clean.return_value = (
            True,
            "",
            {"title": "Title", "original_text": "Article text"},
        )
        self.run_ai.return_value = {
            "status": "completed",
            "analysis": {
                "core": {"summary": "Grounded summary"},
                "theme": "Science",
                "genre": "scientific",
            },
            "exams": [{"quizzes": []}],
        }

        result = module.process_single_article(article_id="article-1", url="https://example.com/a")

        self.assertEqual(result, {"status": "completed", "article_id": "article-1"})
        self.crawl.assert_called_once_with("https://example.com/a")
        self.clean.assert_called_once_with(self.crawl.return_value)
        self.assertEqual(self.update_article.call_count, 2)
        first_update = self.update_article.call_args_list[0]
        self.assertEqual(first_update.args[0], "article-1")
        self.assertEqual(first_update.args[1]["status"], "processing")
        second_update = self.update_article.call_args_list[1]
        self.assertEqual(second_update.args[1]["ai_status"], "completed")
        self.add_vector.assert_called_once_with(
            gold_id="article-1",
            summary="Grounded summary",
            title="Title",
            url="https://example.com/a",
            theme="Science",
            genre="scientific",
        )

    def test_crawl_failure_marks_article_failed_and_stops_workflow(self):
        module = self.build_module()
        self.crawl.return_value = {"success": False, "error": "unreachable"}

        result = module.process_single_article(article_id="article-2", url="https://example.com/b")

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"], "unreachable")
        self.update_article.assert_called_once_with(
            "article-2", {"status": "failed", "error_message": "unreachable"}
        )
        self.clean.assert_not_called()
        self.run_ai.assert_not_called()
        self.add_vector.assert_not_called()


class OrchestratorCharacterizationTests(TestCase):
    def build_module(self):
        self.clean = Mock()
        self.add_vector = Mock()
        self.crawl = Mock()
        self.update_article = Mock(return_value=True)
        self.get_article = Mock()
        self.run_ai = Mock()
        self.get_pipe = Mock()

        dependencies = {
            "pipeline.etl.jobs.clean_logic": dependency(
                "pipeline.etl.jobs.clean_logic",
                clean_and_validate_article=self.clean,
            ),
            "database.Chroma.operations": dependency(
                "database.Chroma.operations", add_article_vector=self.add_vector
            ),
            "database.Crawler.scraper": dependency(
                "database.Crawler.scraper", crawl_article_content=self.crawl
            ),
            "database.Mongo.crud": dependency(
                "database.Mongo.crud",
                update_article_document=self.update_article,
                get_article_document_by_id=self.get_article,
            ),
            "pipeline.etl.jobs.generate_questions": dependency(
                "pipeline.etl.jobs.generate_questions", run_ai_pipeline=self.run_ai
            ),
            "pipeline.etl.registry": dependency(
                "pipeline.etl.registry", get_pipe=self.get_pipe
            ),
            "pipeline.etl.pipes": dependency("pipeline.etl.pipes"),
        }
        return load_legacy_module(
            "legacy_orchestrator_for_test",
            "orchestrator.py",
            dependencies,
        )

    def test_article_task_delegates_to_registered_single_article_pipe(self):
        module = self.build_module()
        pipe = Mock()
        pipe.invoke.return_value = {
            "status": "completed",
            "results": {"process_single_article": {"status": "completed"}},
        }
        self.get_pipe.return_value = pipe

        result = module.execute_article_pipeline_task("article-3", "https://example.com/c")

        self.get_pipe.assert_called_once_with("single_article_pipe")
        pipe.invoke.assert_called_once_with(
            article_id="article-3", url="https://example.com/c"
        )
        self.assertEqual(result, {"status": "completed"})

    def test_ai_only_task_updates_article_and_vector_index(self):
        module = self.build_module()
        self.get_article.return_value = {
            "original_text": "Article text",
            "title": "Title",
            "url": "https://example.com/d",
        }
        self.run_ai.return_value = {
            "status": "completed",
            "analysis": {
                "core": {"summary": "Summary"},
                "theme": "Culture",
                "genre": "narrative",
            },
            "exams": [],
        }

        module.execute_ai_only_task("article-4")

        self.run_ai.assert_called_once_with("Article text")
        self.update_article.assert_called_once()
        self.assertEqual(self.update_article.call_args.args[1]["ai_status"], "completed")
        self.add_vector.assert_called_once_with(
            gold_id="article-4",
            summary="Summary",
            title="Title",
            url="https://example.com/d",
            theme="Culture",
            genre="narrative",
        )

    def test_async_entrypoint_starts_named_daemon_thread(self):
        module = self.build_module()
        thread = Mock()

        with patch.object(module.threading, "Thread", return_value=thread) as thread_type:
            module.run_article_pipeline_async("article-5", "https://example.com/e")

        thread_type.assert_called_once_with(
            target=module.execute_article_pipeline_task,
            args=("article-5", "https://example.com/e"),
            name="ArticlePipeline-article-5",
            daemon=True,
        )
        thread.start.assert_called_once_with()


class SmartParaphraseCharacterizationTests(TestCase):
    def build_module(self):
        decorator = lambda _name, **_metadata: lambda function: function
        dependencies = {
            "pipeline.etl.registry": dependency(
                "pipeline.etl.registry", job=decorator
            )
        }
        return load_legacy_module(
            "legacy_paraphrase_logic_for_test",
            "etl/jobs/paraphrase_logic.py",
            dependencies,
        )

    def test_cache_hit_returns_existing_payload_without_llm(self):
        module = self.build_module()
        cached = {"paraphrased_text": "simple", "start_index": 1, "end_index": 2}

        result = module.logic_smart_paraphrase_llm(
            cached,
            "hard",
            "A hard sentence.",
            "article-6",
            "hash",
            2,
            6,
        )

        self.assertEqual(result, {"paraphrase_data": cached})

    def test_cache_miss_generates_and_preserves_source_offsets(self):
        module = self.build_module()
        run_llm = Mock(
            return_value={"expanded_text": "hard", "paraphrased_text": "difficult"}
        )
        ai_module = dependency(
            "pipeline.ai_core.graphs.smart_paraphrase",
            run_smart_paraphrase_llm=run_llm,
        )

        with patch.dict(
            "sys.modules", {"pipeline.ai_core.graphs.smart_paraphrase": ai_module}
        ):
            result = module.logic_smart_paraphrase_llm(
                {},
                "hard",
                "A hard sentence.",
                "article-7",
                "hash",
                2,
                6,
            )

        payload = result["paraphrase_data"]
        self.assertEqual(payload["paraphrased_text"], "difficult")
        self.assertEqual(payload["start_index"], 2)
        self.assertEqual(payload["end_index"], 6)
        run_llm.assert_called_once_with("hard", "A hard sentence.")
