"""Tests for the new clean architecture orchestration workflows."""

from unittest import TestCase
from unittest.mock import Mock, patch

from service.domain.enums import AIStatus, ArticleStage
from service.orchestration.jobs.enrichment import process_single_article
from service.orchestration.jobs.paraphrase import run_paraphrase_llm
from service.orchestrator import OrchestrationFacade


class SingleArticleWorkflowTests(TestCase):
    @patch("service.orchestration.jobs.enrichment.crawl_article_content")
    @patch("database.Minio.crud.save_bronze_html")
    @patch("database.Minio.crud.save_bronze_meta")
    @patch("service.orchestration.jobs.processing._clean_and_validate")
    @patch("database.Minio.crud.save_silver_clean")
    @patch("service.orchestration.jobs.enrichment.update_article_stage")
    @patch("service.orchestration.jobs.enrichment.update_ai_status")
    @patch("service.orchestration.jobs.enrichment.update_article_title")
    @patch("service.orchestration.jobs.enrichment._run_question_generator")
    @patch("service.orchestration.jobs.enrichment.save_gold_enriched")
    @patch("service.orchestration.jobs.enrichment.save_exam")
    @patch("service.orchestration.jobs.enrichment.add_article_vector")
    def test_successful_workflow(
        self, mock_add_vector, mock_save_exam, mock_save_gold, mock_run_ai,
        mock_update_title, mock_update_ai, mock_update_stage, mock_save_silver,
        mock_clean, mock_save_meta, mock_save_html, mock_crawl
    ):
        mock_crawl.return_value = {"success": True, "html_content": "html", "title": "Title"}
        mock_clean.return_value = (True, "", {"title": "Title", "original_text": "Article text"})
        mock_run_ai.return_value = {
            "status": "completed",
            "analysis": {
                "core": {"summary": "Grounded summary"},
                "theme": "Science",
                "genre": "scientific",
            },
            "exams": [],
        }

        result = process_single_article(article_id="article-1", url="https://example.com/a")

        self.assertEqual(result, {"status": "completed", "article_id": "article-1"})
        mock_crawl.assert_called_once_with("https://example.com/a")
        mock_clean.assert_called_once()
        mock_update_ai.assert_any_call("article-1", AIStatus.IN_PROGRESS)
        mock_update_ai.assert_any_call("article-1", AIStatus.COMPLETED)
        mock_update_stage.assert_any_call("article-1", ArticleStage.SILVER)
        mock_update_stage.assert_any_call("article-1", ArticleStage.GOLD)
        mock_add_vector.assert_called_once_with(
            gold_id="article-1",
            summary="Grounded summary",
            title="Title",
            url="https://example.com/a",
            theme="Science",
            genre="scientific",
        )

    @patch("service.orchestration.jobs.enrichment.crawl_article_content")
    @patch("service.orchestration.jobs.enrichment.update_ai_status")
    def test_crawl_failure_stops_workflow(self, mock_update_ai, mock_crawl):
        mock_crawl.return_value = {"success": False, "error": "unreachable"}

        result = process_single_article(article_id="article-2", url="https://example.com/b")

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"], "unreachable")
        mock_update_ai.assert_called_once_with("article-2", AIStatus.FAILED, "unreachable")


class OrchestratorTests(TestCase):
    @patch("service.orchestrator.get_pipe")
    def test_article_task_delegates_to_registered_single_article_pipe(self, mock_get_pipe):
        pipe = Mock()
        pipe.invoke.return_value = {
            "status": "completed",
            "results": {"process_single_article": {"status": "completed"}},
        }
        mock_get_pipe.return_value = pipe

        result = OrchestrationFacade.execute_article_task("article-3", "https://example.com/c")

        mock_get_pipe.assert_called_once_with("single_article_pipe")
        pipe.invoke.assert_called_once_with(
            article_id="article-3", url="https://example.com/c"
        )
        self.assertEqual(result, {"status": "completed"})

    @patch("service.orchestrator.get_article_document_by_id")
    @patch("database.Minio.crud.read_silver_clean")
    @patch("service.ai_core.graphs.question_generator.graph.app.invoke")
    @patch("database.Minio.crud.save_gold_enriched")
    @patch("database.Mongo.exams.save_exam")
    @patch("database.Mongo.article_index.update_article_stage")
    @patch("service.orchestrator.update_ai_status")
    @patch("database.Chroma.operations.add_article_vector")
    def test_ai_only_task_updates_article_and_vector_index(
        self, mock_add_vector, mock_update_ai, mock_update_stage, mock_save_exam,
        mock_save_gold, mock_invoke, mock_read_silver, mock_get_article
    ):
        mock_get_article.return_value = {"title": "Title", "url": "https://url.com"}
        mock_read_silver.return_value = {"original_text": "Original text"}
        mock_invoke.return_value = {
            "semantic_analysis": {
                "theme": "Culture",
                "genre": "narrative",
                "core": {"summary": "Summary"},
            },
            "final_exam": {}
        }

        from service.orchestration.configuration import get_pipe
        get_pipe("ai_only_pipe").invoke(article_id="article-4")

        mock_invoke.assert_called_once_with({"original_text": "Original text"})
        mock_save_gold.assert_called_once()
        mock_save_exam.assert_called_once()
        mock_update_stage.assert_called_once_with("article-4", ArticleStage.GOLD)
        mock_update_ai.assert_called_with("article-4", AIStatus.COMPLETED)
        mock_add_vector.assert_called_once_with(
            gold_id="article-4",
            summary="Summary",
            title="Title",
            url="https://url.com",
            theme="Culture",
            genre="narrative",
        )


class SmartParaphraseTests(TestCase):
    def test_cache_hit_returns_existing_payload_without_llm(self):
        cached = {"paraphrased_text": "simple", "start_index": 1, "end_index": 2}
        result = run_paraphrase_llm(
            cached_paraphrase=cached,
            highlighted_text="hard",
            paragraph_text="A hard sentence.",
            article_id="article-6",
            paragraph_hash="hash",
            start_idx=2,
            end_idx=6,
        )
        self.assertEqual(result, {"paraphrase_data": cached})

    @patch("service.ai_core.platform.get_ai_tool")
    def test_cache_miss_generates_and_preserves_source_offsets(self, mock_get_tool):
        mock_tool = Mock()
        mock_res = Mock()
        mock_res.output = {"expanded_text": "hard", "paraphrased_text": "difficult"}
        mock_tool.run.return_value = mock_res
        mock_get_tool.return_value = mock_tool

        result = run_paraphrase_llm(
            cached_paraphrase=None,
            highlighted_text="hard",
            paragraph_text="A hard sentence.",
            article_id="article-7",
            paragraph_hash="hash",
            start_idx=2,
            end_idx=6,
        )

        payload = result["paraphrase_data"]
        self.assertEqual(payload["paraphrased_text"], "difficult")
        self.assertEqual(payload["start_index"], 2)
        self.assertEqual(payload["end_index"], 6)
        mock_tool.run.assert_called_once()
