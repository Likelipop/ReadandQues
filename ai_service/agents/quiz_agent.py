"""
ai_service/agents/quiz_agent.py — Dedicated Reading Comprehension Quiz Sub-Agent.

Implements the Quiz Sub-Graph workflow:
fetch_article -> generate_quiz -> validate_quiz -> END.
All comments and docstrings are in English.
"""

import asyncio
import logging
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from ai_service.quiz_generator.generator import generate_questions
from ai_service.quiz_generator.schemas import ExamOutput, QuizItem

try:
    import service.infrastructure.mongo.article_store as article_store
except ImportError:
    import ReadAndQues.service.infrastructure.mongo.article_store as article_store

logger = logging.getLogger(__name__)


class QuizSubGraphState(TypedDict):
    article_id: str
    article_text: str
    quizzes: list[dict[str, Any]]
    summary: str
    error: str


# ── Sub-Graph Nodes ───────────────────────────────────────────────────────────


def fetch_article_node(state: QuizSubGraphState) -> QuizSubGraphState:
    """Fetch article text from store if not already present in state."""
    text = state.get("article_text", "").strip()
    article_id = state.get("article_id", "").strip()

    if not text and article_id:
        try:
            doc = article_store.get_gold_content(article_id)
            if doc:
                text = (doc.get("cleaned_text") or doc.get("original_text") or "").strip()
        except Exception as e:
            logger.warning(f"[QuizSubAgent] Could not fetch article text for {article_id}: {e}")

    state["article_text"] = text
    if not text:
        state["error"] = "No article text available to generate a quiz. Please open an article in ReadSpace first."
    return state


def generate_quiz_node(state: QuizSubGraphState) -> QuizSubGraphState:
    """Generate structured IELTS-style questions from article text."""
    if state.get("error"):
        return state

    text = state.get("article_text", "").strip()
    try:
        from unittest.mock import MagicMock
        if isinstance(generate_questions, MagicMock):
            exam_output = generate_questions(text)
        else:
            exam_output = generate_questions(text)

        quizzes: list[dict[str, Any]] = [
            q.model_dump() if hasattr(q, "model_dump") else q
            for q in getattr(exam_output, "quizzes", [])
        ]

        if not quizzes:
            state["error"] = "Quiz generator returned empty questions list."
            return state

        summary_text = (
            exam_output.semantic_analysis.summary
            if getattr(exam_output, "semantic_analysis", None)
            else ""
        )

        state["quizzes"] = quizzes
        state["summary"] = summary_text

    except Exception as e:
        logger.error(f"[QuizSubAgent] Question generation failed: {e}")
        state["error"] = f"Quiz generation error: {e}"

    return state


def validate_quiz_node(state: QuizSubGraphState) -> QuizSubGraphState:
    """Validate quiz items have questions and correct answers."""
    if state.get("error"):
        return state

    valid_quizzes = []
    for q in state.get("quizzes", []):
        if isinstance(q, dict) and q.get("question") and q.get("correct_answer"):
            valid_quizzes.append(q)

    if not valid_quizzes and not state.get("error"):
        state["error"] = "Validation failed: No valid quiz questions produced."

    state["quizzes"] = valid_quizzes
    return state


# ── Sub-Graph Builder ─────────────────────────────────────────────────────────


def build_quiz_subgraph():
    """Build and compile the Quiz Sub-Agent workflow."""
    workflow = StateGraph(QuizSubGraphState)
    workflow.add_node("fetch_article", fetch_article_node)
    workflow.add_node("generate_quiz", generate_quiz_node)
    workflow.add_node("validate_quiz", validate_quiz_node)

    workflow.set_entry_point("fetch_article")
    workflow.add_edge("fetch_article", "generate_quiz")
    workflow.add_edge("generate_quiz", "validate_quiz")
    workflow.add_edge("validate_quiz", END)

    return workflow.compile()


_quiz_subgraph = None


def get_quiz_subgraph():
    """Singleton getter for compiled Quiz Sub-Agent."""
    global _quiz_subgraph
    if _quiz_subgraph is None:
        _quiz_subgraph = build_quiz_subgraph()
    return _quiz_subgraph


def run_quiz_subagent(article_id: str = "", article_text: str = "") -> dict[str, Any]:
    """
    Synchronously invoke the Quiz Sub-Agent.
    """
    subgraph = get_quiz_subgraph()
    initial_state: QuizSubGraphState = {
        "article_id": article_id,
        "article_text": article_text,
        "quizzes": [],
        "summary": "",
        "error": "",
    }
    result = subgraph.invoke(initial_state)
    return {
        "quizzes": result.get("quizzes", []),
        "summary": result.get("summary", ""),
        "error": result.get("error", ""),
    }


# ── Compatibility node for LangGraph or legacy calls ─────────────────────────


async def quiz_node(state: Any) -> Any:
    """
    Quiz node wrapper delegating to the Quiz Sub-Agent.
    Maintains compatibility with AgentState and LangGraph workflows.
    """
    text = state.get("article_text", "").strip()
    article_id = state.get("article_id", "").strip()

    result = await asyncio.to_thread(run_quiz_subagent, article_id=article_id, article_text=text)

    quizzes = result.get("quizzes", [])
    error = result.get("error", "")
    summary = result.get("summary", "")

    if error:
        state["error"] = error
        state["response"] = (
            f"**⚠️ Cannot generate quiz:** {error}\n\n"
            "Please open an article in **ReadSpace** before generating reading comprehension questions."
        )
        state["quiz_data"] = []
        state["action_type"] = "chat"
        return state

    state["quiz_data"] = quizzes
    state["action_type"] = "quiz"
    state["citations"] = []
    state["response"] = (
        f"### 📝 Reading Comprehension Quiz Ready!\n\n"
        f"Generated **{len(quizzes)}** questions based on the current passage.\n\n"
        + (f"**Passage Summary:** {summary}\n\n" if summary else "")
        + "👉 Practice directly using the quiz panel."
    )
    return state
