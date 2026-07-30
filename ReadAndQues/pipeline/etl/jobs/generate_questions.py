import logging
import uuid
from datetime import datetime, timezone

from database.Chroma.operations import add_article_vector
from database.Mongo.crud import (get_unprocessed_silver_docs, insert_gold_doc,
                                 insert_pipeline_log)
from pipeline.ai_core.graphs.question_generator.graph import app as graph_app
from pipeline.etl.config import BATCH_SIZE
from pipeline.etl.registry import job

logger = logging.getLogger(__name__)


def run_ai_pipeline(text: str) -> dict | None:
    session_id = f"session_{uuid.uuid4().hex}"
    graph_config = {"configurable": {"thread_id": session_id}}
    state_input = {"original_text": text}
    try:
        final_state = graph_app.invoke(state_input, config=graph_config)
        return {
            "status": "completed",
            "analysis": final_state.get("semantic_analysis", {}),
            "exams": [final_state.get("final_exam", {})],
        }
    except Exception as e:
        logger.error(f"Error invoking AI graph: {e}")
        return None


@job("generate_questions")
def generate_questions(**kwargs):
    max_docs = kwargs.get("max_docs", BATCH_SIZE)
    silver_docs = get_unprocessed_silver_docs()[:max_docs]

    if not silver_docs:
        logger.info("No unprocessed silver docs found.")
        return {"processed": 0, "success": 0}

    success_count = 0
    for s_doc in silver_docs:
        silver_id = s_doc["_str_id"]
        url = s_doc.get("url")
        original_text = s_doc.get("original_text", "")
        title = s_doc.get("title", "")
        
        logger.info(f"Generating questions for {silver_id} ({url})")
        ai_result = run_ai_pipeline(original_text)
        
        if not ai_result:
            logger.warning(f"AI generation failed for {silver_id}")
            insert_pipeline_log(
                stage="gold",
                status="failed",
                message="AI pipeline failed to generate exam",
                document_id=silver_id,
                url=url,
            )
            continue
            
        gold_doc = {
            "silver_id": silver_id,
            "url": url,
            "title": title,
            "original_text": original_text,
            "source_name": s_doc.get("source_name", ""),
            "image_url": s_doc.get("image_url", ""),
            "theme": ai_result["analysis"].get("theme", "General"),
            "genre": ai_result["analysis"].get("genre", "general"),
            "word_count": s_doc.get("word_count", 0),
            "analysis": ai_result["analysis"],
            "exams": ai_result["exams"],
            "status": "completed",
            "created_at": datetime.now(timezone.utc),
        }
        
        try:
            gold_id = insert_gold_doc(gold_doc)
            summary = (
                ai_result["analysis"].get("core", {}).get("summary")
                or ai_result["analysis"].get("theme")
                or title
            )
            if summary:
                add_article_vector(
                    gold_id=gold_id,
                    summary=summary,
                    title=title,
                    url=url,
                    theme=gold_doc.get("theme", "General"),
                    genre=gold_doc.get("genre", "general"),
                )
            success_count += 1
            logger.info(f"Generated questions and saved to gold: {gold_id}")
        except Exception as e:
            logger.error(f"Failed to save gold doc for {silver_id}: {e}")

    logger.info(f"Generate questions finished. Success: {success_count}/{len(silver_docs)}")
    return {"processed": len(silver_docs), "success": success_count}
