"""
service/orchestrator.py — Unified Orchestration Facade for ReadAndQues.
"""

import logging
import threading
from typing import Any, Dict

from database.Mongo.article_index import update_ai_status
from database.Mongo.crud import get_article_document_by_id, update_article_document
from service.domain.enums import AIStatus
from service.orchestration.configuration import get_pipe
import service.orchestration.pipes  # noqa: F401

logger = logging.getLogger(__name__)


class OrchestrationFacade:
    """Thin facade unifying all asynchronous and batch orchestration entrypoints."""

    @staticmethod
    def execute_article_task(article_id: str, url: str) -> Dict[str, Any]:
        logger.info("🔄 Starting background pipeline task for article_id=%s, url=%s", article_id, url)
        pipe = get_pipe("single_article_pipe")
        result = pipe.invoke(article_id=article_id, url=url)
        job_result = result.get("results", {}).get("process_single_article", {})
        if not job_result:
            job_result = {"status": "failed", "error": "Pipeline invocation failed."}
        return job_result

    @staticmethod
    def run_article_pipeline_async(article_id: str, url: str) -> None:
        thread = threading.Thread(
            target=execute_article_pipeline_task,
            args=(article_id, url),
            name=f"ArticlePipeline-{article_id}",
            daemon=True,
        )
        thread.start()
        logger.info("🚀 Spawned background thread for article_id=%s", article_id)

    @staticmethod
    def execute_ai_only_task(article_id: str) -> None:
        """
        Re-run AI enrichment for an article that has already been ingested.
        Reads original_text from the silver MinIO layer.
        """
        logger.info("🤖 Starting AI-only background task for article_id=%s", article_id)

        from database.Minio.crud import read_silver_clean
        from database.Chroma.operations import add_article_vector
        from database.Mongo.exams import save_exam
        from database.Mongo.article_index import update_article_stage
        from service.domain.enums import ArticleStage
        from service.ai_core.graphs.question_generator.graph import app as question_graph
        from database.Minio.crud import save_gold_enriched
        from datetime import datetime, timezone

        # Read article index
        doc = get_article_document_by_id(article_id)
        if not doc:
            logger.error("❌ Article not found for AI task: %s", article_id)
            return

        # Try to get original_text from Silver MinIO
        silver_doc = read_silver_clean(article_id)
        original_text = (silver_doc or {}).get("original_text") or doc.get("original_text", "")
        title = doc.get("title", "")
        url = doc.get("url", "")

        if not original_text:
            update_ai_status(article_id, AIStatus.FAILED, "No original text found.")
            logger.error("❌ No original text for article_id=%s", article_id)
            return

        update_ai_status(article_id, AIStatus.IN_PROGRESS)

        try:
            final_state = question_graph.invoke({"original_text": original_text})
            analysis = final_state.get("semantic_analysis", {})
            exams_list = [final_state.get("final_exam", {})]

            gold_doc = {
                "article_id": article_id,
                "url": url,
                "title": title,
                "theme": analysis.get("theme", "General"),
                "genre": analysis.get("genre", "general"),
                "summary": analysis.get("core", {}).get("summary", ""),
                "analysis": analysis,
                "exams": exams_list,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            save_gold_enriched(article_id, gold_doc)
            save_exam(article_id, gold_doc)
            update_article_stage(article_id, ArticleStage.GOLD)
            update_ai_status(article_id, AIStatus.COMPLETED)

            summary = gold_doc["summary"] or title
            if summary:
                add_article_vector(
                    gold_id=article_id,
                    summary=summary,
                    title=title,
                    url=url,
                    theme=gold_doc["theme"],
                    genre=gold_doc["genre"],
                )

            logger.info("✅ AI-only task completed for article_id=%s", article_id)
        except Exception as e:
            logger.exception("⚠️ Unhandled exception in AI task for article_id=%s: %s", article_id, e)
            update_ai_status(article_id, AIStatus.FAILED, str(e))

    @staticmethod
    def run_ai_only_pipeline_async(article_id: str) -> None:
        thread = threading.Thread(
            target=execute_ai_only_task,
            args=(article_id,),
            name=f"AIOnlyPipeline-{article_id}",
            daemon=True,
        )
        thread.start()
        logger.info("🚀 Spawned AI-only background thread for article_id=%s", article_id)

    @staticmethod
    def run_daily_pipeline(max_news: int = None) -> dict[str, str]:
        logger.info("🕘 Daily pipeline started")
        kwargs = {}
        if max_news is not None:
            kwargs["max_links"] = max_news
            kwargs["max_docs"] = max_news
            logger.info(f"Using max_news overriding: {max_news}")

        # 3 pipes: ingest → process → enrich (silver→gold merged with AI)
        pipes_to_run = [
            "ingest_bronze_pipe",
            "bronze_to_silver_pipe",
            "silver_to_gold_pipe",
        ]

        for pipe_name in pipes_to_run:
            try:
                res = get_pipe(pipe_name).invoke(**kwargs)
                if res.get("status") == "failed":
                    err = res.get("results", {})
                    logger.error(f"❌ Daily pipeline failed at stage '{pipe_name}': {err}")
                    return {
                        "status": "failed",
                        "message": f"Daily pipeline failed at stage '{pipe_name}'",
                    }
            except Exception as e:
                logger.error(f"❌ Pipeline execution error in '{pipe_name}': {e}")
                return {"status": "failed", "message": f"Pipeline '{pipe_name}' execution error: {e}"}

        return {"status": "completed", "message": "Daily pipeline processed successfully"}


# Top-level helper aliases for backward compatibility
execute_article_pipeline_task = OrchestrationFacade.execute_article_task
run_article_pipeline_async = OrchestrationFacade.run_article_pipeline_async
execute_ai_only_task = OrchestrationFacade.execute_ai_only_task
run_ai_only_pipeline_async = OrchestrationFacade.run_ai_only_pipeline_async
run_daily_pipeline = OrchestrationFacade.run_daily_pipeline
