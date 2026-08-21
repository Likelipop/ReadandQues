import unittest
from unittest.mock import Mock, patch

import service.ai_core.tools  # noqa: F401
from service.ai_core.graphs.smart_paraphrase.graph import (
    generator_node,
    run_smart_paraphrase_flow,
    should_continue,
    validator_node,
)
from service.ai_core.graphs.smart_paraphrase.schemas import SmartParaphraseState
from service.ai_core.platform import get_ai_tool


class SmartInkFlowTests(unittest.TestCase):
    def test_ai_core_tool_registration(self):
        tool = get_ai_tool("smart_paraphrase")
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "smart_paraphrase")

    def test_smart_paraphrase_generator_node(self):
        """Test LangGraph generator node with mock LLM."""
        mock_gen_output = {
            "expanded_text": "pedagogical models",
            "paraphrased_text": "educational teaching methods",
            "explanation": "Pedagogical relates directly to instructional strategies.",
        }

        with patch("service.ai_core.graphs.smart_paraphrase.graph.get_llm") as mock_get_llm:
            mock_get_llm.return_value = Mock()

            state: SmartParaphraseState = {
                "highlighted_text": "pedagogical models",
                "paragraph_context": "The university adopted modern pedagogical models.",
                "expanded_text": "",
                "paraphrased_text": "",
                "explanation": "",
                "is_valid": False,
                "validation_feedback": "",
                "retry_count": 0,
            }

            with patch("langchain_core.runnables.base.RunnableSequence.invoke", return_value=mock_gen_output):
                gen_res = generator_node(state)
                self.assertEqual(gen_res["paraphrased_text"], "educational teaching methods")
                self.assertEqual(gen_res["retry_count"], 1)

    def test_smart_paraphrase_validator_node(self):
        """Test LangGraph validator node."""
        mock_val_output = {
            "is_valid": True,
            "feedback": "Accurate paraphrase.",
        }

        with patch("service.ai_core.graphs.smart_paraphrase.graph.get_llm") as mock_get_llm:
            mock_get_llm.return_value = Mock()

            state: SmartParaphraseState = {
                "highlighted_text": "pedagogical models",
                "paragraph_context": "The university adopted modern pedagogical models.",
                "expanded_text": "pedagogical models",
                "paraphrased_text": "educational teaching methods",
                "explanation": "Accurate synonym.",
                "is_valid": False,
                "validation_feedback": "",
                "retry_count": 1,
            }

            with patch("langchain_core.runnables.base.RunnableSequence.invoke", return_value=mock_val_output):
                val_res = validator_node(state)
                self.assertTrue(val_res["is_valid"])

    def test_should_continue_logic(self):
        valid_state: SmartParaphraseState = {
            "highlighted_text": "test",
            "paragraph_context": "test",
            "expanded_text": "test",
            "paraphrased_text": "test",
            "explanation": "",
            "is_valid": True,
            "validation_feedback": "",
            "retry_count": 1,
        }
        self.assertEqual(should_continue(valid_state), "end")

        invalid_state: SmartParaphraseState = {
            "highlighted_text": "test",
            "paragraph_context": "test",
            "expanded_text": "test",
            "paraphrased_text": "test",
            "explanation": "",
            "is_valid": False,
            "validation_feedback": "Not accurate",
            "retry_count": 1,
        }
        self.assertEqual(should_continue(invalid_state), "generate")

        max_retry_state: SmartParaphraseState = {
            "highlighted_text": "test",
            "paragraph_context": "test",
            "expanded_text": "test",
            "paraphrased_text": "test",
            "explanation": "",
            "is_valid": False,
            "validation_feedback": "",
            "retry_count": 3,
        }
        self.assertEqual(should_continue(max_retry_state), "end")
