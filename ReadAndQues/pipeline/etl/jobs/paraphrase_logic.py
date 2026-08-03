import logging
from pipeline.etl.registry import job

logger = logging.getLogger(__name__)

@job("logic_smart_paraphrase_llm", inputs=["cached_paraphrase", "highlighted_text", "paragraph_text", "article_id", "paragraph_hash", "start_idx", "end_idx"], outputs=["paraphrase_data"])
def logic_smart_paraphrase_llm(
    cached_paraphrase: dict,
    highlighted_text: str,
    paragraph_text: str,
    article_id: str,
    paragraph_hash: str,
    start_idx: int,
    end_idx: int
):
    # If we got a cache hit from the previous job, just return it.
    if cached_paraphrase:
        logger.info(f"Cache hit for smart paraphrase in article {article_id}")
        # The cache contains expanded_text, paraphrased_text, start_index, end_index
        return {"paraphrase_data": cached_paraphrase}

    logger.info(f"Cache miss. Generating smart paraphrase for article {article_id}")
    from pipeline.ai_core.graphs.smart_paraphrase import run_smart_paraphrase_llm
    
    result = run_smart_paraphrase_llm(highlighted_text, paragraph_text)
    
    expanded_text = result.get("expanded_text", highlighted_text)
    paraphrased_text = result.get("paraphrased_text", highlighted_text)

    # Find the new start and end index of the expanded text in the paragraph
    new_start_idx = paragraph_text.find(expanded_text)
    if new_start_idx == -1:
        # Fallback if LLM hallucinated the text slightly
        new_start_idx = start_idx
        new_end_idx = end_idx
        expanded_text = highlighted_text
    else:
        new_end_idx = new_start_idx + len(expanded_text)

    paraphrase_data = {
        "article_id": article_id,
        "paragraph_hash": paragraph_hash,
        "user_highlighted_text": highlighted_text,
        "user_start_index": start_idx,
        "user_end_index": end_idx,
        "original_expanded_text": expanded_text,
        "paraphrased_text": paraphrased_text,
        "start_index": new_start_idx,
        "end_index": new_end_idx
    }

    return {"paraphrase_data": paraphrase_data}
