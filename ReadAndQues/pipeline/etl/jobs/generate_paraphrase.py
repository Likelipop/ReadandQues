import logging
import uuid
from datetime import datetime, timezone

from database.Mongo.crud import (get_unprocessed_gold_docs,
                                 insert_paraphrase, insert_pipeline_log)
from pipeline.ai_core.graphs.paraphrase_generator.graph import app as paraphrase_app
from pipeline.etl.config import BATCH_SIZE
from pipeline.etl.registry import job

logger = logging.getLogger(__name__)

def run_paraphrase_pipeline(text: str) -> list[dict] | None:
    session_id = f"session_{uuid.uuid4().hex}"
    graph_config = {"configurable": {"thread_id": session_id}}
    state_input = {"text": text, "phrases": []}
    try:
        final_state = paraphrase_app.invoke(state_input, config=graph_config)
        return final_state.get("phrases", [])
    except Exception as e:
        logger.error(f"Error invoking paraphrase graph: {e}")
        return None

@job("generate_paraphrase")
def generate_paraphrase(**kwargs):
    max_docs = kwargs.get("max_docs", BATCH_SIZE)
    gold_docs = get_unprocessed_gold_docs()[:max_docs]

    if not gold_docs:
        logger.info("No unprocessed gold docs found for paraphrase generation.")
        return {"processed": 0, "success": 0}

    success_count = 0
    for doc in gold_docs:
        gold_id = doc["_str_id"]
        summary = doc.get("analysis", {}).get("core", {}).get("summary", "")
        
        if not summary:
            continue
            
        logger.info(f"Generating paraphrase for gold_id: {gold_id}")
        
        phrases = run_paraphrase_pipeline(summary)
        
        if not phrases:
            logger.warning(f"Failed to generate paraphrase for {gold_id}")
            insert_pipeline_log(
                stage="platinum_paraphrase",
                status="failed",
                message="AI pipeline failed to generate paraphrase",
                document_id=gold_id,
            )
            continue
            
        try:
            # Format output
            formatted_phrases = []
            for i, p in enumerate(phrases):
                formatted_phrases.append({
                    "id": f"p{i+1}",
                    "original_text": p.get("original_text", ""),
                    "alternatives": p.get("alternatives", [])
                })
                
            paraphrase_doc = {
                "article_id": gold_id,
                "original_summary": summary,
                "phrases": formatted_phrases,
                "created_at": datetime.now(timezone.utc),
            }
            
            insert_paraphrase(paraphrase_doc)
            success_count += 1
            logger.info(f"Successfully generated paraphrase for {gold_id}")
            
        except Exception as e:
            logger.error(f"Failed to insert paraphrase for {gold_id}: {e}")
            insert_pipeline_log(
                stage="platinum_paraphrase",
                status="failed",
                message=str(e),
                document_id=gold_id,
            )
            
    logger.info(f"Generate paraphrase finished. Success: {success_count}/{len(gold_docs)}")
    return {"processed": len(gold_docs), "success": success_count}
