import json
import logging
from datetime import datetime, timezone

from langchain.prompts import PromptTemplate

from database.Mongo.crud import (get_unprocessed_gold_docs,
                                 insert_paraphrase, insert_pipeline_log)
from pipeline.ai_core.connection import get_llm
from pipeline.etl.config import BATCH_SIZE
from pipeline.etl.registry import job

logger = logging.getLogger(__name__)

PARAPHRASE_PROMPT = """
You are an expert English language teacher.
Extract 2-4 key phrases from the following summary text. 
For each phrase, provide 2-3 alternative ways to express the same idea in different contexts.

Input summary text:
{text}

Output ONLY valid JSON in the following format:
[
  {{
    "original_text": "the key phrase from text",
    "alternatives": ["alternative 1", "alternative 2"]
  }}
]
"""

@job("generate_paraphrase")
def generate_paraphrase(**kwargs):
    max_docs = kwargs.get("max_docs", BATCH_SIZE)
    gold_docs = get_unprocessed_gold_docs()[:max_docs]

    if not gold_docs:
        logger.info("No unprocessed gold docs found for paraphrase generation.")
        return {"processed": 0, "success": 0}

    llm = get_llm(temperature=0.7)
    prompt = PromptTemplate(template=PARAPHRASE_PROMPT, input_variables=["text"])
    chain = prompt | llm

    success_count = 0
    for doc in gold_docs:
        gold_id = doc["_str_id"]
        summary = doc.get("analysis", {}).get("core", {}).get("summary", "")
        
        if not summary:
            continue
            
        logger.info(f"Generating paraphrase for gold_id: {gold_id}")
        try:
            response = chain.invoke({"text": summary})
            # Parse the JSON response
            content = response.content
            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "").strip()
            elif content.startswith("```"):
                content = content.replace("```", "").strip()
                
            phrases = json.loads(content)
            
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
            logger.error(f"Failed to generate paraphrase for {gold_id}: {e}")
            insert_pipeline_log(
                stage="platinum_paraphrase",
                status="failed",
                message=str(e),
                document_id=gold_id,
            )
            
    logger.info(f"Generate paraphrase finished. Success: {success_count}/{len(gold_docs)}")
    return {"processed": len(gold_docs), "success": success_count}
