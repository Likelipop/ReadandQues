"""
ReadAndQues/service/tests/test_ai_functional_suite.py
Comprehensive QA Functional Test Suite for AI Core Components.

Validates:
1. Model Routing & Fallback Fault Tolerance (Azure -> OpenAI -> Ollama)
2. Question Generator Direct LangChain Structured Output Flow
3. Contextual Explainer & Token Streaming (Dynamic prompt, academic fallback)
4. Grounding & RAG Retrieval (BM25 tokenized retrieval, passage proofs)
5. AI Platform Tool Policy & Cache Management
"""

from unittest import TestCase
from unittest.mock import MagicMock, Mock, patch

import service.ai_core.tools  # noqa: F401
from service.ai_core.connection.router import ModelRouter, get_llm
from service.ai_core.graphs import (
    ExamOutput,
    QuizItem,
    SemanticAnalysis,
    generate_questions,
    run_explained_flow,
    run_question_generator_flow,
    stream_explained_tokens,
)
from service.ai_core.grounding import chunk_article_text, retrieve_article_chunks
from service.ai_core.platform import AIToolPolicy


class AIFunctionalTestSuite(TestCase):
    def setUp(self):
        self.sample_passage = (
            "Perovskite solar cells promise conversion efficiencies exceeding 30 percent. "
            "Unlike traditional silicon wafers, perovskite thin films can be printed on flexible substrates at low temperatures. "
            "However, long-term stability against moisture and thermal degradation remains a major commercialization barrier."
        )

    # ── 1. Model Routing & Multi-Provider Fallbacks ──────────────────────────

    def test_model_router_primary_azure_selection(self):
        """QA Test: Router prioritizes primary provider in fallback list."""
        mock_factory = Mock(return_value=Mock())
        with patch("service.ai_core.connection.router.get_all_providers", return_value={"azure": mock_factory}):
            router = ModelRouter(fallback_order=["azure"])
            llm = router.get_llm(temperature=0.2)
            self.assertIsNotNone(llm)
            mock_factory.assert_called_once_with(0.2)

    def test_model_router_fallback_to_openai_when_azure_offline(self):
        """QA Test: Router cascades to next available provider if primary raises error."""
        def faulty_azure(temp):
            raise ConnectionError("Azure down")

        mock_openai = Mock(return_value=Mock())
        with patch("service.ai_core.connection.router.get_all_providers", return_value={"azure": faulty_azure, "openai": mock_openai}):
            router = ModelRouter(fallback_order=["azure", "openai"])
            llm = router.get_llm(temperature=0.7)
            self.assertIsNotNone(llm)
            mock_openai.assert_called_once_with(0.7)

    def test_model_router_fallback_to_local_ollama_when_cloud_offline(self):
        """QA Test: Router cascades to self-hosted Ollama if cloud providers fail."""
        def faulty_provider(temp):
            raise ConnectionError("Cloud offline")

        mock_ollama = Mock(return_value=Mock())
        with patch("service.ai_core.connection.router.get_all_providers", return_value={"azure": faulty_provider, "openai": faulty_provider, "ollama": mock_ollama}):
            router = ModelRouter(fallback_order=["azure", "openai", "ollama"])
            llm = router.get_llm(temperature=0.0)
            self.assertIsNotNone(llm)
            mock_ollama.assert_called_once_with(0.0)

    # ── 2. Question Generator Structured Output Flow ─────────────────────────

    def test_generate_questions_structured_output(self):
        """QA Test: Structured output directly produces validated ExamOutput schema."""
        mock_quizzes = [
            QuizItem(
                quiz_type="multiple_choice",
                question="What efficiency level do perovskite solar cells promise?",
                options=["Exceeding 30 percent", "Under 10 percent", "50 percent", "0 percent"],
                correct_answer="Exceeding 30 percent",
                supporting_text="perovskite solar cells promise conversion efficiencies exceeding 30 percent",
                explanation="The passage states over 30 percent.",
            )
        ]
        mock_exam_output = ExamOutput(
            quizzes=mock_quizzes,
            semantic_analysis=SemanticAnalysis(
                genre="scientific",
                theme="Science",
                summary="Passage discusses perovskite solar cells.",
            ),
        )
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value.invoke.return_value = mock_exam_output

        with patch("service.ai_core.graphs.model.question_generator.get_llm", return_value=mock_llm):
            result = generate_questions(self.sample_passage)
            self.assertEqual(len(result.quizzes), 1)
            self.assertEqual(result.quizzes[0].correct_answer, "Exceeding 30 percent")
            self.assertIsNotNone(result.semantic_analysis)
            self.assertEqual(result.semantic_analysis.genre, "scientific")

    def test_run_question_generator_flow_formatting(self):
        """QA Test: Flow produces complete dictionary output compatible with pipelines."""
        mock_quizzes = [
            QuizItem(
                quiz_type="multiple_choice",
                question="What efficiency level do perovskite solar cells promise?",
                options=["Exceeding 30 percent", "Under 10 percent", "50 percent", "0 percent"],
                correct_answer="Exceeding 30 percent",
                supporting_text="perovskite solar cells promise conversion efficiencies exceeding 30 percent",
                explanation="The passage states over 30 percent.",
            )
        ]
        mock_exam_output = ExamOutput(
            quizzes=mock_quizzes,
            semantic_analysis=SemanticAnalysis(
                genre="scientific",
                theme="Science",
                summary="Passage discusses perovskite solar cells.",
            ),
        )
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value.invoke.return_value = mock_exam_output

        with patch("service.ai_core.graphs.model.question_generator.get_llm", return_value=mock_llm):
            res = run_question_generator_flow(self.sample_passage)
            self.assertTrue(res["_verifier_passed"])
            self.assertEqual(len(res["raw_quizzes"]), 1)
            self.assertEqual(len(res["verified_quizzes"]), 1)
            self.assertIn("exam_id", res["final_exam"])
            self.assertEqual(res["final_exam"]["total_questions"], 1)
            self.assertEqual(res["semantic_analysis"]["theme"], "Science")

    # ── 3. Contextual Explainer & Streaming Tests ──────────────────────────────

    def test_stream_explained_token_generation(self):
        """QA Test: Explainer stream yields markdown tokens for clicked phrase."""
        mock_chunks = [MagicMock(content="**💡 In Simple Words:**\n"), MagicMock(content="Solar power is clean energy.")]
        mock_chain = MagicMock()
        mock_chain.stream.return_value = iter(mock_chunks)

        with patch("service.ai_core.graphs.model.explained.get_llm", return_value=MagicMock()), \
             patch("langchain_core.prompts.PromptTemplate.__or__", return_value=mock_chain):
            tokens = list(stream_explained_tokens("solar power", paragraph_context=self.sample_passage))
            full_text = "".join(tokens)
            self.assertIn("In Simple Words", full_text)
            self.assertIn("Solar power", full_text)

    def test_stream_explained_offline_fallback_generator(self):
        """QA Test: When LLM is completely offline, explainer stream gracefully uses academic fallback."""
        with patch("service.ai_core.graphs.model.explained.get_llm", side_effect=RuntimeError("LLM Offline")):
            tokens = list(stream_explained_tokens("perovskite solar cells", paragraph_context=self.sample_passage))
            self.assertGreater(len(tokens), 0)
            full_text = "".join(tokens)
            self.assertIn("In Simple Words", full_text)

    def test_run_explained_flow_synchronous_wrapper(self):
        """QA Test: Synchronous explained wrapper aggregates stream into structured response."""
        with patch("service.ai_core.graphs.model.explained.stream_explained_tokens", return_value=iter(["**💡 In Simple Words:**\n", "Simplified text."])):
            res = run_explained_flow("perovskite", paragraph_context=self.sample_passage)
            self.assertEqual(res["phrase"], "perovskite")
            self.assertIn("Simplified text", res["detailed_explanation"])

    # ── 4. Grounding & RAG Retrieval Tests ────────────────────────────────────

    def test_chunk_article_text_deterministic_splitting(self):
        """QA Test: Semantic chunking groups text into coherent chunks with offsets and token counts."""
        text = self.sample_passage
        chunks = chunk_article_text(text)
        self.assertGreaterEqual(len(chunks), 1)
        self.assertEqual(chunks[0].chunk_id, "chunk_0")
        self.assertTrue(len(chunks[0].content_hash) > 0)
        self.assertGreater(chunks[0].token_count, 0)
        self.assertGreater(chunks[0].sentence_count, 0)

    def test_retrieve_article_chunks_bm25_ranking(self):
        """QA Test: Lexical retrieval accurately matches query terms."""
        chunks = chunk_article_text(self.sample_passage)
        retrieved = retrieve_article_chunks(chunks, query="flexible substrates printing", top_k=1)
        self.assertEqual(len(retrieved), 1)
        self.assertIn("flexible substrates", retrieved[0].text)

    # ── 5. AI Policy & Execution Engine Tests ──────────────────────────────────

    def test_ai_tool_policy_caching_mechanism(self):
        """QA Test: Policy caches execution output on identical input, bypassing duplicate LLM calls."""
        call_counter = {"count": 0}

        def mock_llm_execution():
            call_counter["count"] += 1
            return {"result": f"processed_{call_counter['count']}"}

        input_payload = {"prompt": "What is the capital of France?"}
        res1 = AIToolPolicy.execute("geo_tool", "1.0.0", mock_llm_execution, input_payload, use_cache=True)
        self.assertEqual(res1.output["result"], "processed_1")

        res2 = AIToolPolicy.execute("geo_tool", "1.0.0", mock_llm_execution, input_payload, use_cache=True)
        self.assertEqual(res2.output["result"], "processed_1")
        self.assertEqual(call_counter["count"], 1)

    def test_ai_tool_policy_error_isolation(self):
        """QA Test: Unhandled exception in tool logic is caught and recorded as failed status."""
        def faulty_tool():
            raise ZeroDivisionError("Math error inside AI graph")

        res = AIToolPolicy.execute("faulty_tool", "1.0.0", faulty_tool, {}, use_cache=False)
        self.assertEqual(res.status, "failed")
        self.assertIn("Math error inside AI graph", res.error)
