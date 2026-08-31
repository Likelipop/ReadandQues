"""
ReadAndQues/service/tests/test_ai_functional_suite.py
Comprehensive QA Functional Test Suite for AI Core Components.

Validates:
1. Azure OpenAI Model Connection & Initialization
2. Question Generator Direct LangChain Structured Output Flow
3. Contextual Explainer & Token Streaming (Dynamic prompt, academic fallback)
4. Grounding & RAG Retrieval (BM25 tokenized retrieval, passage proofs)
"""

from unittest import TestCase
from unittest.mock import MagicMock, Mock, patch

from ai_service.connection import ModelRouter, get_azure_llm, get_llm
from ai_service.quiz_generator import (
    ExamOutput,
    QuizItem,
    SemanticAnalysis,
    generate_questions,
    run_explained_flow,
    run_question_generator_flow,
    stream_explained_tokens,
)
from ai_service.rag.grounding import chunk_article_text, retrieve_article_chunks


class AIFunctionalTestSuite(TestCase):
    def setUp(self):
        self.sample_passage = (
            "Perovskite solar cells promise conversion efficiencies exceeding 30 percent. "
            "Unlike traditional silicon wafers, perovskite thin films can be printed on flexible substrates at low temperatures. "
            "However, long-term stability against moisture and thermal degradation remains a major commercialization barrier."
        )

    # ── 1. Azure Model Connection & Configuration Tests ───────────────────────

    def test_get_azure_llm_initialization(self):
        """QA Test: Azure LLM initializes with configured deployment name and temperature."""
        with patch.dict(
            "os.environ",
            {
                "AZURE_OPENAI_API_KEY": "test-key",
                "AZURE_OPENAI_ENDPOINT": "https://test.services.ai.azure.com",
                "AZURE_DEPLOYMENT_NAME": "gpt-4o-mini",
            },
        ):
            llm = get_azure_llm(temperature=0.4)
            self.assertEqual(llm.deployment_name, "gpt-4o-mini")
            self.assertEqual(llm.temperature, 0.4)

    def test_get_llm_missing_api_key_raises_error(self):
        """QA Test: Missing API key properly raises ValueError."""
        with patch.dict("os.environ", {"AZURE_OPENAI_API_KEY": ""}):
            with self.assertRaises(ValueError):
                get_llm()

    def test_model_router_wrapper(self):
        """QA Test: ModelRouter wrapper correctly returns Azure LLM."""
        with patch("ai_service.connection.get_azure_llm", return_value=Mock()) as mock_get:
            router = ModelRouter()
            llm = router.get_llm(temperature=0.2)
            self.assertIsNotNone(llm)
            mock_get.assert_called_once_with(temperature=0.2)

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

        with patch("ai_service.quiz_generator.generator.get_llm", return_value=mock_llm):
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

        with patch("ai_service.quiz_generator.generator.get_llm", return_value=mock_llm):
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
        mock_chunks = [
            MagicMock(content="**💡 In Simple Words:**\n"),
            MagicMock(content="Solar power is clean energy."),
        ]
        mock_chain = MagicMock()
        mock_chain.stream.return_value = iter(mock_chunks)

        with (
            patch("ai_service.explainer.explainer.get_llm", return_value=MagicMock()),
            patch("langchain_core.prompts.PromptTemplate.__or__", return_value=mock_chain),
        ):
            tokens = list(stream_explained_tokens("solar power", paragraph_context=self.sample_passage))
            full_text = "".join(tokens)
            self.assertIn("In Simple Words", full_text)
            self.assertIn("Solar power", full_text)

    def test_stream_explained_offline_fallback_generator(self):
        """QA Test: When LLM is completely offline, explainer stream gracefully uses academic fallback."""
        with patch("ai_service.explainer.explainer.get_llm", side_effect=RuntimeError("LLM Offline")):
            tokens = list(stream_explained_tokens("perovskite solar cells", paragraph_context=self.sample_passage))
            self.assertGreater(len(tokens), 0)
            full_text = "".join(tokens)
            self.assertIn("In Simple Words", full_text)

    def test_run_explained_flow_synchronous_wrapper(self):
        """QA Test: Synchronous explained wrapper aggregates stream into structured response."""
        with patch(
            "ai_service.explainer.explainer.stream_explained_tokens",
            return_value=iter(["**💡 In Simple Words:**\n", "Simplified text."]),
        ):
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
