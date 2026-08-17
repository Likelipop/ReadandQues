"""
ReadAndQues/readspace/tests/test_rag_chat_functional.py
Functional tests for the RAG StudyBuddy Chat System, Server-Sent Events (SSE) streaming,
and LangGraph dynamic agent router.
"""

import json
from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse

from service.domain.enums import AgentIntent
from service.rag.router import (
    RouterState,
    build_rag_router_graph,
    classify_intent_node,
    execute_rag_pipeline,
    route_intent_edge,
)
from service.rag.schemas import Citation, RAGResponse


class RAGChatFunctionalTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.article_id = "art-rag-test-001"
        self.mock_rag_response = {
            "status": "success",
            "query": "What are the main causes of ocean microplastics?",
            "intent": "news",
            "answer": "Microplastics mainly originate from synthetic textiles, tire wear, and degraded plastic waste.",
            "citations": [
                {
                    "source": "Paragraph 2",
                    "chunk_id": "chunk-101",
                    "quote": "Synthetic textiles and tire wear generate the majority of microscopic particles.",
                }
            ],
            "retrieved_chunks_count": 2,
            "model_used": "gpt-4o-mini",
        }

    # ── 1. SSE Streaming Endpoint Tests ────────────────────────────────────────

    def test_rag_stream_api_missing_question_returns_400(self):
        """Streaming endpoint requires a non-empty question payload."""
        response = self.client.post(
            reverse("readspace:rag_stream_api"),
            data=json.dumps({"question": "", "article_id": self.article_id}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["status"], "error")
        self.assertIn("Question required", data["message"])

    def test_rag_stream_api_invalid_json_returns_400(self):
        """Malformed JSON payload returns 400 Bad Request."""
        response = self.client.post(
            reverse("readspace:rag_stream_api"),
            data="not-valid-json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_rag_stream_api_streams_sse_events(self):
        """Streaming endpoint yields metadata, deltas, and [DONE] terminal event."""
        with patch("service.services.ask_rag_question", return_value=self.mock_rag_response):
            response = self.client.post(
                reverse("readspace:rag_stream_api"),
                data=json.dumps({
                    "question": "What are the main causes of ocean microplastics?",
                    "article_id": self.article_id,
                }),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Type"], "text/event-stream")
            self.assertEqual(response["Cache-Control"], "no-cache")
            self.assertEqual(response["X-Accel-Buffering"], "no")

            # Collect streaming content chunks
            streamed_lines = [
                line.decode("utf-8")
                for line in response.streaming_content
                if line.decode("utf-8").strip()
            ]

            # Verify first event is metadata with citations
            first_line = streamed_lines[0]
            self.assertTrue(first_line.startswith("data: "))
            first_payload = json.loads(first_line.replace("data: ", ""))
            self.assertEqual(first_payload["type"], "metadata")
            self.assertEqual(len(first_payload["citations"]), 1)
            self.assertEqual(first_payload["citations"][0]["chunk_id"], "chunk-101")

            # Verify intermediate delta events contain words
            delta_lines = [line for line in streamed_lines if '"type": "delta"' in line]
            self.assertGreater(len(delta_lines), 0)
            full_reconstructed_text = "".join(
                json.loads(line.replace("data: ", ""))["text"] for line in delta_lines
            )
            self.assertIn("Microplastics mainly originate from synthetic textiles", full_reconstructed_text)

            # Verify terminal event
            last_line = streamed_lines[-1]
            self.assertEqual(last_line.strip(), "data: [DONE]")

    # ── 2. LangGraph Router & Intent Classifier Tests ──────────────────────────

    def test_classify_intent_node_fallback_when_no_api_key(self):
        """Intent classifier defaults to NEWS with confidence when no API key configured."""
        with patch.dict("os.environ", {}, clear=True):
            initial_state: RouterState = {
                "question": "Explain paragraph 1",
                "article_id": self.article_id,
                "intent": "unknown",
                "confidence": 0.0,
                "answer": "",
                "citations": [],
                "retrieved_chunks_count": 0,
                "model_used": "",
            }
            output_state = classify_intent_node(initial_state)
            self.assertEqual(output_state["intent"], AgentIntent.NEWS.value)
            self.assertGreaterEqual(output_state["confidence"], 0.5)

    def test_route_intent_edge_selection(self):
        """Router conditional edge resolves known intents."""
        news_state: RouterState = {
            "question": "What is the topic?",
            "article_id": None,
            "intent": "news",
            "confidence": 0.95,
            "answer": "",
            "citations": [],
            "retrieved_chunks_count": 0,
            "model_used": "",
        }
        self.assertEqual(route_intent_edge(news_state), "news_agent")

    def test_execute_rag_pipeline_end_to_end_mocked(self):
        """Full LangGraph pipeline returns typed RAGResponse with answer and citations."""
        mock_citations = [
            Citation(article_id="art-1", title="Ocean Plastic", url="https://example.com/art-1")
        ]
        mock_news_response = RAGResponse(
            status="success",
            query="Tell me about ocean plastic",
            intent=AgentIntent.NEWS,
            answer="Ocean plastic is a growing threat.",
            citations=mock_citations,
            retrieved_chunks_count=1,
            model_used="gpt-4o-mini",
        )

        with patch("service.rag.router.run_news_agent", return_value=mock_news_response):
            response = execute_rag_pipeline(
                question="Tell me about ocean plastic",
                article_id=self.article_id,
            )
            self.assertEqual(response.status, "success")
            self.assertEqual(response.intent, AgentIntent.NEWS)
            self.assertEqual(response.answer, "Ocean plastic is a growing threat.")
            self.assertEqual(len(response.citations), 1)

    # ── 3. Error Resilience & Downstream Fallbacks ──────────────────────────────

    def test_ask_rag_question_service_handles_exception_gracefully(self):
        """When RAG pipeline encounters unexpected error, service returns structured error response."""
        from service.services import ask_rag_question

        with patch("service.rag.router.execute_rag_pipeline", side_effect=RuntimeError("ChromaDB connection timeout")):
            result = ask_rag_question(question="What is this?", article_id=self.article_id)
            self.assertEqual(result["status"], "error")
            self.assertIn("Error executing RAG", result["answer"])
            self.assertEqual(result["citations"], [])
