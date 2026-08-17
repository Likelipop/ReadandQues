from unittest import TestCase
from unittest.mock import patch

import service.ai_core.tools  # noqa: F401
from service.ai_core.graphs.ask_article.graph import node_verify_grounding
from service.ai_core.grounding import chunk_article_text, retrieve_article_chunks
from service.ai_core.platform import get_ai_tool


class GroundedQuestionTicketTests(TestCase):
    def test_chunk_article_text_offsets_and_hashes(self):
        text = "First paragraph about solar power.\n\nSecond paragraph about wind energy."
        chunks = chunk_article_text(text)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0].chunk_id, "chunk_0")
        self.assertIn("solar power", chunks[0].text)
        self.assertTrue(len(chunks[0].content_hash) > 0)
        self.assertEqual(chunks[1].chunk_id, "chunk_1")
        self.assertIn("wind energy", chunks[1].text)

    def test_retrieve_article_chunks_scoped_matching(self):
        text = "First paragraph about solar power.\n\nSecond paragraph about wind energy."
        chunks = chunk_article_text(text)
        matched = retrieve_article_chunks(chunks, "solar energy", top_k=1)
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0].chunk_id, "chunk_0")

    def test_node_verify_grounding_valid_citation(self):
        retrieved = [{"chunk_id": "chunk_0", "text": "Solar power is a renewable resource."}]
        state = {
            "answer": "Solar energy is renewable.",
            "citation_quote": "Solar power is a renewable resource.",
            "retrieved_chunks": retrieved,
            "is_grounded": True,
        }
        res = node_verify_grounding(state)
        self.assertEqual(res["answer"], "Solar energy is renewable.")
        self.assertTrue(res["is_grounded"])

    def test_node_verify_grounding_rejects_unverified_quote(self):
        retrieved = [{"chunk_id": "chunk_0", "text": "Solar power is a renewable resource."}]
        state = {
            "answer": "Fusion power was discovered in 2025.",
            "citation_quote": "Fusion power is infinite.",
            "retrieved_chunks": retrieved,
            "is_grounded": True,
        }
        res = node_verify_grounding(state)
        self.assertEqual(res["answer"], "not_found_in_article")
        self.assertFalse(res["is_grounded"])

    def test_ask_article_tool_execution(self):
        tool = get_ai_tool("ask_article")
        self.assertEqual(tool.name, "ask_article")

        with patch("service.ai_core.tools.ask_article_tool.run_ask_article_flow") as mock_flow:
            mock_flow.return_value = {
                "ticket_id": "TKT-12345",
                "question": "What is solar?",
                "answer": "Solar power is renewable.",
                "citation_quote": "Solar power",
                "status": "RESOLVED",
                "timestamp": "12:00:00",
                "is_grounded": True,
            }
            res = tool.run({"article_text": "Solar power is renewable.", "question": "What is solar?"})
            self.assertEqual(res.status, "completed")
            self.assertEqual(res.output["ticket_id"], "TKT-12345")
            self.assertEqual(res.output["answer"], "Solar power is renewable.")
            self.assertEqual(res.output["status"], "RESOLVED")

