"""
pipeline/etl/platinum.py — Platinum stage: Interactive paraphrase generation.
"""

import logging
from datetime import datetime, timezone
import os
import sys
import django
from pydantic import BaseModel, Field

# Ensure Django is setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ReadAndQues.settings")
django.setup()

from pipeline.ai_core.connection import get_llm
from database.Mongo.crud import get_unprocessed_gold_docs, insert_pipeline_log, insert_paraphrase

logger = logging.getLogger(__name__)

class PhraseAlternative(BaseModel):
    id: str = Field(..., description="Unique ID for this phrase (e.g., p1, p2)")
    original_text: str = Field(..., description="The exact phrase from the summary")
    alternatives: list[str] = Field(..., description="3 alternative phrasings for this text")

class ParaphraseOutput(BaseModel):
    phrases: list[PhraseAlternative] = Field(..., description="List of swappable phrases")


def process_platinum():
    logger.info("═══════════════════════════════════════════════")
    logger.info("  💎 PLATINUM STAGE — Paraphrase Generation")
    logger.info("═══════════════════════════════════════════════")

    unprocessed = get_unprocessed_gold_docs()
    if not unprocessed:
        logger.info("Nothing to process. Done.")
        return

    stats = {"completed": 0, "failed": 0}

    for doc in unprocessed:
        gold_id = doc["_str_id"]
        url = doc.get("url", "???")
        
        # Only process if we have a summary
        summary = doc.get("analysis", {}).get("core", {}).get("summary")
        if not summary:
            continue

        prompt = f"""
You are an expert editor. Below is a summary of an article.
I want to create an interactive "living text" card.
Identify 3 to 10 short phrases or vocabulary (1 to 8 words) in the summary that can be paraphrased without changing the overall meaning of the sentence.
For each phrase, provide exactly 3 alternative phrasings that fit perfectly in the original sentence grammatically and semantically.

Summary:
{summary}
"""
        
        try:
            llm = get_llm(temperature=0.7)
            structured_llm = llm.with_structured_output(ParaphraseOutput)
            result: ParaphraseOutput = structured_llm.invoke(prompt)
            
            paraphrase_doc = {
                "article_id": gold_id,
                "original_summary": summary,
                "phrases": [p.model_dump() for p in result.phrases],
                "created_at": datetime.now(timezone.utc)
            }
            
            insert_paraphrase(paraphrase_doc)
            stats["completed"] += 1
            
            insert_pipeline_log(
                stage="platinum",
                status="completed",
                message="Paraphrase generation completed",
                document_id=gold_id,
                url=url,
            )
            
        except Exception as e:
            stats["failed"] += 1
            logger.error(f"  ⚠️  Platinum generation failed [{gold_id}]: {e}")
            insert_pipeline_log(
                stage="platinum",
                status="error",
                message=str(e),
                document_id=gold_id,
                url=url,
            )

    insert_pipeline_log(
        stage="platinum_batch",
        status="completed",
        message=f"Completed: {stats['completed']}, Failed: {stats['failed']}",
    )


def main():
    process_platinum()


if __name__ == "__main__":
    main()
