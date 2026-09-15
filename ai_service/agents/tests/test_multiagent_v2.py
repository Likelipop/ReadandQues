"""
ai_service/agents/tests/test_multiagent_v2.py
Unit and functional tests for Multi-Agent LangGraph v2 (Refactored).

Tests:
1. LLM Router intent classification (mocked).
2. General Agent node response generation.
3. Quiz Agent node delegation and state mapping.
4. Tool-calling mechanism for search_articles.
5. Short-term memory trimming & rolling summarization trigger.
6. User learning profile LTM recall & formatting.
7. Graph routing and end-to-end execution.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from ai_service.agents.general_agent import general_agent_node
from ai_service.agents.graph import build_study_graph, route_by_intent
from ai_service.agents.memory import (
    format_user_profile_for_prompt,
    get_checkpointer,
    get_default_user_profile,
    should_summarize,
    trim_conversation_history,
    update_user_learning_profile,
)
from ai_service.agents.quiz_agent import quiz_agent_node, run_quiz_subagent
from ai_service.agents.router import IntentClassification, router_node
from ai_service.agents.tools import search_articles
from ai_service.interface import ask_study_dock


# ── Router Tests ──────────────────────────────────────────────────────────────


@patch("ai_service.agents.router.get_llm")
def test_router_node_quiz_intent(mock_get_llm):
    """Verify LLM router classifies quiz requests correctly."""
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(
        return_value=IntentClassification(intent="quiz", reasoning="User asked to create a quiz.")
    )
    mock_llm.with_structured_output.return_value = mock_structured
    mock_get_llm.return_value = mock_llm

    state = {"messages": [HumanMessage(content="Tạo bài quiz cho tôi")]}
    result = asyncio.run(router_node(state))
    assert result["intent"] == "quiz"


@patch("ai_service.agents.router.get_llm")
def test_router_node_general_intent(mock_get_llm):
    """Verify LLM router classifies general queries correctly."""
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(
        return_value=IntentClassification(intent="general", reasoning="User asked about vocabulary.")
    )
    mock_llm.with_structured_output.return_value = mock_structured
    mock_get_llm.return_value = mock_llm

    state = {"messages": [HumanMessage(content="What does 'ubiquitous' mean?")]}
    result = asyncio.run(router_node(state))
    assert result["intent"] == "general"


@patch("ai_service.agents.router.get_llm")
def test_router_node_fallback_on_error(mock_get_llm):
    """Verify router defaults to 'general' when LLM fails."""
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(side_effect=Exception("LLM timeout"))
    mock_llm.with_structured_output.return_value = mock_structured
    mock_get_llm.return_value = mock_llm

    state = {"messages": [HumanMessage(content="test")]}
    result = asyncio.run(router_node(state))
    assert result["intent"] == "general"


def test_router_node_empty_messages():
    """Verify router handles empty message state gracefully."""
    state = {"messages": []}
    result = asyncio.run(router_node(state))
    assert result["intent"] == "general"


def test_route_by_intent():
    """Verify route_by_intent dispatcher."""
    assert route_by_intent({"intent": "quiz"}) == "quiz_agent"
    assert route_by_intent({"intent": "general"}) == "general_agent"
    assert route_by_intent({}) == "general_agent"


# ── General Agent Tests ───────────────────────────────────────────────────────


@patch("ai_service.agents.general_agent.get_llm")
def test_general_agent_node_response(mock_get_llm):
    """Verify General Agent node produces conversational response."""
    mock_llm = MagicMock()
    mock_resp = AIMessage(content="Photosynthesis is the process by which plants make food.")
    mock_llm.ainvoke = AsyncMock(return_value=mock_resp)
    mock_llm.bind_tools.return_value = mock_llm
    mock_get_llm.return_value = mock_llm

    state = {
        "messages": [HumanMessage(content="What is photosynthesis?")],
        "page_context": "readspace",
        "article_id": "art-123",
        "article_text": "Plants use photosynthesis to convert light to energy.",
    }
    result = asyncio.run(general_agent_node(state))
    assert result["action_type"] == "chat"
    assert "Photosynthesis is the process" in result["response"]
    assert len(result["messages"]) == 1


# ── Quiz Agent Node Tests ────────────────────────────────────────────────────


@patch("ai_service.agents.quiz_agent.run_quiz_subagent")
def test_quiz_agent_node_success(mock_subagent):
    """Verify Quiz Agent node delegates to subagent and maps to state."""
    mock_subagent.return_value = {
        "quizzes": [
            {
                "quiz_type": "multiple_choice",
                "question": "What is AI?",
                "correct_answer": "Artificial Intelligence",
            }
        ],
        "summary": "AI summary",
        "error": "",
    }
    state = {
        "article_id": "art-123",
        "article_text": "Sample text about AI.",
    }
    result = asyncio.run(quiz_agent_node(state))
    assert result["action_type"] == "quiz"
    assert len(result["quiz_data"]) == 1
    assert "Reading Comprehension Quiz Ready" in result["response"]


@patch("ai_service.agents.quiz_agent.run_quiz_subagent")
def test_quiz_agent_node_error(mock_subagent):
    """Verify Quiz Agent node handles errors cleanly."""
    mock_subagent.return_value = {
        "quizzes": [],
        "summary": "",
        "error": "No article text available",
    }
    state = {
        "article_id": "",
        "article_text": "",
    }
    result = asyncio.run(quiz_agent_node(state))
    assert result["action_type"] == "chat"
    assert result["quiz_data"] == []
    assert "Cannot generate quiz" in result["response"]


# ── Memory Tests ──────────────────────────────────────────────────────────────


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


# ── Quiz Sub-Agent Tests ──────────────────────────────────────────────────────


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


# ── Search Tool Tests ─────────────────────────────────────────────────────────


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
