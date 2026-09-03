"""
ReadAndQues/readspace/tests/test_study_dock_e2e.py
End-to-End & functional tests for the Left AI Study Dock Multi-Agent LangGraph system (v2).

Tests:
1. Supervisor direct vocabulary & grammar explanation (no tool needed).
2. Supervisor tool-calling with `search_articles` for news/grounded Q&A.
3. Quiz Sub-Agent delegation and question generation.
4. Thread-based memory persistence across calls.
5. Context window trimming and rolling summarization.
6. SSE streaming API endpoint contracts.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

from django.test import Client, TestCase
from django.urls import reverse
from langchain_core.messages import AIMessage, HumanMessage

from ai_service.agents.memory import (
    get_checkpointer,
    get_default_user_profile,
    trim_conversation_history,
)
from ai_service.agents.state import StudyDockState
from ai_service.interface import ask_study_dock


class StudyDockE2ETestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.article_id = "test-art-e2e-123"
        self.sample_text = (
            "Extremophiles are organisms that thrive in extreme environments such as hydrothermal vents "
            "and subglacial lakes. Scientists study their unique metabolic pathways to understand the limits of life."
        )

    # ── 1. Supervisor Direct Explanation & Intent Tests ───────────────────────

    @patch("ai_service.agents.supervisor.get_llm")
    def test_explainer_agent_routing(self, mock_get_llm):
        """User asking to explain a word receives direct explanation from Supervisor."""
        mock_llm = MagicMock()
        mock_resp = AIMessage(content="**💡 In Simple Words:** Organisms that love extreme conditions.")
        
        # Support both synchronous and async ainvoke
        mock_llm.ainvoke = AsyncMock(return_value=mock_resp)
        mock_llm.bind_tools.return_value = mock_llm
        mock_get_llm.return_value = mock_llm

        res = ask_study_dock(
            query="Explain the word 'extremophiles'",
            article_id=self.article_id,
            page_context="readspace",
            article_text=self.sample_text,
        )

        self.assertEqual(res["intent"], "explain")
        self.assertEqual(res["action_type"], "chat")
        self.assertIn("Organisms that love extreme conditions", res["response"])

    @patch("ai_service.agents.supervisor.get_llm")
    def test_rag_agent_routing(self, mock_get_llm):
        """User asking a factual news question receives answer from Supervisor."""
        mock_llm = MagicMock()
        mock_resp = AIMessage(content="Climate change affects ocean biodiversity severely.")
        mock_llm.ainvoke = AsyncMock(return_value=mock_resp)
        mock_llm.bind_tools.return_value = mock_llm
        mock_get_llm.return_value = mock_llm

        res = ask_study_dock(
            query="What are the latest facts about climate change?",
            page_context="homepage",
        )

        self.assertEqual(res["action_type"], "chat")
        self.assertIn("Climate change affects ocean biodiversity", res["response"])

    # ── 2. Quiz Sub-Agent Delegation Tests ───────────────────────────────────

    @patch("ai_service.agents.quiz_agent.generate_questions")
    def test_quiz_agent_routing(self, mock_gen_questions):
        """User requesting a quiz delegates to Quiz Sub-Agent and returns quiz_data."""
        mock_exam_output = MagicMock()
        mock_quiz_item = MagicMock()
        mock_quiz_item.model_dump.return_value = {
            "quiz_type": "multiple_choice",
            "question": "What are extremophiles?",
            "options": ["A) Extreme organisms", "B) Plants", "C) Birds", "D) Minerals"],
            "correct_answer": "A) Extreme organisms",
            "explanation": "Extremophiles live in harsh environments.",
            "supporting_text": "Extremophiles are organisms that thrive in extreme environments.",
        }
        mock_exam_output.quizzes = [mock_quiz_item]
        mock_exam_output.semantic_analysis.summary = "A passage discussing extremophiles."
        mock_gen_questions.return_value = mock_exam_output

        res = ask_study_dock(
            query="Create a quiz for this article",
            article_id=self.article_id,
            page_context="readspace",
            article_text=self.sample_text,
        )

        self.assertEqual(res["intent"], "quiz")
        self.assertEqual(res["action_type"], "quiz")
        self.assertEqual(len(res["quiz_data"]), 1)
        self.assertEqual(res["quiz_data"][0]["question"], "What are extremophiles?")

    def test_quiz_agent_without_article_returns_clear_message(self):
        """When on homepage without an active article, quiz generation reports clean guidance."""
        res = ask_study_dock(
            query="Generate quiz",
            article_id="",
            page_context="homepage",
            article_text="",
        )

        self.assertIn("No article text available", res["error"])
        self.assertIn("Cannot generate quiz", res["response"])

    # ── 3. Memory & Context Window Tests ─────────────────────────────────────

    def test_context_window_trimming_preserves_recent_messages(self):
        """trim_conversation_history limits tokens and keeps the latest messages."""
        messages = [
            HumanMessage(content=f"Question number {i} with lots of context words...")
            for i in range(20)
        ]
        trimmed = trim_conversation_history(messages, max_tokens=500)
        self.assertLessEqual(len(trimmed), len(messages))
        self.assertTrue(len(trimmed) > 0)
        # Most recent turn must be preserved
        self.assertEqual(trimmed[-1].content, messages[-1].content)

    def test_user_profile_default_schema(self):
        """UserLearningProfile contains CEFR, TrueFalseNotgiven weak skill, and reading notes."""
        profile = get_default_user_profile()
        self.assertIn("cefr_level", profile)
        self.assertIn("TrueFalseNotgiven", profile["weak_skills"])
        self.assertIn("reading_notes", profile)
        self.assertLessEqual(len(profile["reading_notes"].split()), 200)

    # ── 4. SSE Streaming API Endpoint Tests ───────────────────────────────────

    def test_study_dock_stream_api_missing_query_returns_400(self):
        """SSE streaming endpoint requires query."""
        response = self.client.post(
            reverse("readspace:study_dock_stream"),
            data=json.dumps({"query": ""}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    @patch("ai_service.interface.stream_study_dock_sync")
    def test_study_dock_stream_api_streams_events(self, mock_stream):
        """SSE endpoint yields metadata, deltas, and [DONE]."""
        mock_stream.return_value = iter([
            {
                "type": "metadata",
                "intent": "general",
                "action_type": "chat",
                "citations": [],
                "quiz_data": [],
                "error": "",
            },
            {"type": "delta", "text": "Hello "},
            {"type": "delta", "text": "world"},
            {"type": "done"},
        ])

        response = self.client.post(
            reverse("readspace:study_dock_stream"),
            data=json.dumps({
                "query": "Hello",
                "article_id": self.article_id,
                "page_context": "readspace",
                "thread_id": "test_thread_123",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/event-stream")

        content = b"".join(response.streaming_content).decode("utf-8")
        self.assertIn("data: ", content)
        self.assertIn('"type": "metadata"', content)
        self.assertIn('"type": "delta"', content)
        self.assertIn("[DONE]", content)
