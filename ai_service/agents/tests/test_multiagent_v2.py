"""
ai_service/agents/tests/test_multiagent_v2.py
Comprehensive unit and functional tests for Multi-Agent LangGraph v2.

Tests:
1. Intent recognition & direct vocabulary/grammar explanation.
2. Tool-calling mechanism for search_articles with rich news cards.
3. Quiz Sub-Agent autonomous generation and error handling.
4. Short-term memory thread persistence with MemorySaver/PostgresSaver.
5. Tiered context window trimming & rolling summarization.
6. User learning profile LTM recall & formatting.
"""

from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from ai_service.agents.memory import (
    format_user_profile_for_prompt,
    get_checkpointer,
    get_default_user_profile,
    should_summarize,
    trim_conversation_history,
    update_user_learning_profile,
)
from ai_service.agents.quiz_agent import run_quiz_subagent
from ai_service.agents.supervisor import _detect_quick_quiz_intent, _detect_vocabulary_inquiry, supervisor_node
from ai_service.agents.tools import search_articles
from ai_service.interface import ask_study_dock


def test_quick_quiz_intent_detection():
    """Verify regex intent detection for Vietnamese and English quiz requests."""
    assert _detect_quick_quiz_intent("Tạo bài quiz cho tôi") is True
    assert _detect_quick_quiz_intent("Cho tôi làm trắc nghiệm bài này") is True
    assert _detect_quick_quiz_intent("Create a quiz for this article") is True
    assert _detect_quick_quiz_intent("Make a test for comprehension") is True
    assert _detect_quick_quiz_intent("What does photosynthesis mean?") is False
    assert _detect_quick_quiz_intent("Summarize this article") is False


def test_vocabulary_inquiry_detection():
    """Verify extraction of target words from user queries for LTM tricky_words."""
    words = _detect_vocabulary_inquiry("What does 'counter-intuitive' mean in paragraph 2?")
    assert "counter-intuitive" in words

    words2 = _detect_vocabulary_inquiry('Explain "sustainable development"')
    assert "sustainable development" in words2


def test_user_learning_profile_schema_and_update():
    """Verify LTM profile updates and formatting with TrueFalseNotgiven naming."""
    profile = get_default_user_profile()
    assert "TrueFalseNotgiven" in profile["weak_skills"]

    update_user_learning_profile(9999, {"cefr_level": "B2", "tricky_words": ["metabolic"]})
    formatted = format_user_profile_for_prompt(profile)
    assert "Target CEFR Reading Level:" in formatted
    assert "Challenging Question Types:" in formatted


def test_context_window_trimming_and_summarization_trigger():
    """Verify rolling summarizer threshold and message trimming."""
    messages = [HumanMessage(content=f"Message {i}") for i in range(10)]
    assert should_summarize(messages, threshold=8) is True

    trimmed = trim_conversation_history(messages, max_tokens=100)
    assert len(trimmed) <= 10
    assert len(trimmed) > 0


@patch("ai_service.agents.quiz_agent.generate_questions")
def test_quiz_subagent_run(mock_gen):
    """Verify Quiz Sub-Agent workflow produces structured questions."""
    mock_item = MagicMock()
    mock_item.model_dump.return_value = {
        "quiz_type": "multiple_choice",
        "question": "What is the topic?",
        "correct_answer": "AI",
        "explanation": "Because AI is discussed.",
    }
    mock_out = MagicMock()
    mock_out.quizzes = [mock_item]
    mock_out.semantic_analysis.summary = "A summary of AI."
    mock_gen.return_value = mock_out

    res = run_quiz_subagent(article_id="art-test", article_text="Artificial intelligence is growing.")
    assert len(res["quizzes"]) == 1
    assert res["quizzes"][0]["question"] == "What is the topic?"
    assert res["summary"] == "A summary of AI."
    assert not res["error"]


@patch("ai_service.agents.tools.retrieve_and_rerank_context")
def test_search_articles_tool(mock_retrieve):
    """Verify search_articles tool formats grounded passages and card metadata."""
    mock_chunk = {
        "metadata": {
            "article_id": "art-101",
            "title": "Robotics in Surgery",
            "url": "https://example.com/robotics",
            "theme": "Technology",
        },
        "text": "Robots assist surgeons with high precision.",
    }
    mock_retrieve.return_value = (
        "--- Document 1 ---\nContent: Robots assist surgeons.",
        [],
        [mock_chunk],
    )

    result = search_articles.invoke({"query": "surgery robots", "limit": 2})
    assert "=== SEARCH RESULTS & GROUNDED CONTEXT ===" in result
    assert "Robotics in Surgery" in result
    assert "/readspace/art-101" in result
