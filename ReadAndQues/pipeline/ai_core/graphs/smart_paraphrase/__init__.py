import logging
from typing import Dict
from .graph import app

logger = logging.getLogger(__name__)

def run_smart_paraphrase_llm(highlighted_text: str, paragraph_context: str) -> Dict[str, str]:
    """
    Invokes the LangGraph to process a highlighted text with validation.
    """
    initial_state = {
        "highlighted_text": highlighted_text,
        "paragraph_context": paragraph_context,
        "expanded_text": "",
        "paraphrased_text": "",
        "explanation": "",
        "is_valid": False,
        "validation_feedback": "",
        "retry_count": 0
    }
    
    try:
        final_state = app.invoke(initial_state)
        return {
            "expanded_text": final_state.get("expanded_text", highlighted_text),
            "paraphrased_text": final_state.get("paraphrased_text", highlighted_text)
        }
    except Exception as e:
        logger.error(f"Graph execution failed: {e}")
        return {
            "expanded_text": highlighted_text,
            "paraphrased_text": highlighted_text
        }
