"""
ai_service/agents/router.py — LLM-based Intent Classification Router.

Uses structured output to dynamically classify user intent,
replacing hardcoded regex patterns.
"""

import logging
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from ai_service.agents.state import StudyDockState
from ai_service.connection import get_llm

logger = logging.getLogger(__name__)


class IntentClassification(BaseModel):
    """Structured output schema for intent classification."""
    intent: Literal["quiz", "general"] = Field(
        description=(
            "Classify the user's intent. "
            "'quiz' = user explicitly requests generating a quiz, test, or comprehension questions. "
            "'general' = everything else (vocabulary, grammar, article discussion, search, platform questions)."
        )
    )
    reasoning: str = Field(
        description="Brief reasoning for why this intent was chosen."
    )


ROUTER_SYSTEM_PROMPT = """You are an intent classification specialist for the ReadAndQues AI Study platform.

Your ONLY job is to classify the user's message into one of two categories:

1. **quiz**: The user is explicitly asking to GENERATE a quiz, test, comprehension questions, or practice exam.
   Examples: "Create a quiz", "Tạo bài trắc nghiệm", "Test me on this article", "Generate questions", "Cho tôi làm quiz", "Make a comprehension test"

2. **general**: EVERYTHING else — vocabulary questions, grammar explanations, article discussions, search requests, platform questions, greetings, etc.
   Examples: "What does 'ubiquitous' mean?", "Summarize this article", "Find articles about AI", "How does ReadAndQues work?"

Classify based on the user's LATEST message only. When in doubt, choose 'general'."""


async def router_node(state: StudyDockState) -> dict:
    """
    Intent classification node using LLM structured output.
    Routes to quiz_agent or general_agent based on classified intent.
    """
    messages = state.get("messages", [])
    if not messages:
        return {"intent": "general"}

    # Extract last user message
    last_user_msg = next(
        (m for m in reversed(messages) if isinstance(m, HumanMessage)), None
    )
    if not last_user_msg:
        return {"intent": "general"}

    user_query = last_user_msg.content if hasattr(last_user_msg, "content") else str(last_user_msg)
    if isinstance(user_query, list):
        user_query = " ".join(
            b.get("text", "") if isinstance(b, dict) else str(b) for b in user_query
        )

    try:
        llm = get_llm()
        structured_llm = llm.with_structured_output(IntentClassification)
        result = await structured_llm.ainvoke([
            SystemMessage(content=ROUTER_SYSTEM_PROMPT),
            HumanMessage(content=f"Classify this message: \"{user_query}\""),
        ])

        intent = result.intent if isinstance(result, IntentClassification) else "general"
        logger.info(f"[Router] Intent='{intent}' for query='{user_query[:80]}' (reason: {result.reasoning[:100]})")
        return {"intent": intent}

    except Exception as e:
        logger.warning(f"[Router] LLM classification failed ({e}). Defaulting to 'general'.")
        return {"intent": "general"}
