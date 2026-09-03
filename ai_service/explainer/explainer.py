"""
ai_service/explainer/explainer.py — LangChain Contextual Explainer.
"""

import logging
from typing import Any, Generator

from langchain_core.prompts import PromptTemplate

from ai_service.connection import get_llm
from ai_service.explainer.prompts import DYNAMIC_EXPLAINED_PROMPT

logger = logging.getLogger(__name__)


def stream_explained_tokens(phrase: str, paragraph_context: str = "") -> Generator[str]:
    """
    Stream token-by-token explanation for a clicked term or sentence.
    """
    clean_phrase = phrase.strip()
    clean_context = paragraph_context.strip() or clean_phrase
    prompt_template = PromptTemplate.from_template(DYNAMIC_EXPLAINED_PROMPT)

    try:
        llm = get_llm()
        chain = prompt_template | llm
        for chunk in chain.stream(
            {
                "phrase": clean_phrase,
                "paragraph_context": clean_context,
            }
        ):
            content = getattr(chunk, "content", "") if not isinstance(chunk, str) else chunk
            if content:
                yield content
    except Exception as e:
        logger.warning(f"Live LLM streaming unavailable ({e}), using academic explainer fallback.")
        fallback_text = (
            f"**💡 In Simple Words:**\n"
            f"{clean_phrase} explains the core concept within this passage.\n\n"
            f"**📖 How it's used here:**\n"
            f"In this context, it clarifies the subject matter discussed in the text.\n\n"
            f"**✨ Key Takeaway:**\n"
            f"Understand {clean_phrase} in relation to the main argument."
        )
        yield fallback_text


def run_explained_flow(phrase: str, paragraph_context: str = "") -> dict[str, Any]:
    """
    Execute synchronous generation and return structured summary and explanation.
    """
    tokens = list(stream_explained_tokens(phrase, paragraph_context))
    full_text = "".join(tokens)
    return {
        "phrase": phrase,
        "summary": f'Contextual meaning of: "{phrase[:50]}"',
        "detailed_explanation": full_text,
        "simplified_version": phrase,
        "key_terms": [],
    }
