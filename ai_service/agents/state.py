"""
ai_service/agents/state.py — State schema for LangGraph Multi-Agent Study Dock.

Adheres to LangGraph MessagesState pattern for conversational thread memory.
All comments and docstrings are in English.
"""

from typing import Any

from langgraph.graph import MessagesState

from ai_service.quiz_generator.schemas import QuizItem


class StudyDockState(MessagesState):
    """
    Core state schema for the Multi-Agent Study Dock.
    Inherits `messages: list[BaseMessage]` from MessagesState for conversational short-term memory.
    """
    # Context attributes
    article_id: str
    page_context: str  # "readspace" | "homepage" | "all_tests"
    article_text: str
    user_id: int | None

    # Memory attributes
    conversation_summary: str
    user_profile: dict[str, Any]  # CEFR level, topics, tricky words, weak skills

    # Router / Intent classification
    intent: str  # "explain" | "rag" | "quiz" | "general"

    # Agent output attributes
    response: str
    citations: list[dict[str, Any]]
    quiz_data: list[dict[str, Any] | QuizItem]
    action_type: str  # "chat" | "quiz"
    error: str


# Backward compatibility alias
AgentState = StudyDockState

__all__ = ["AgentState", "StudyDockState"]
