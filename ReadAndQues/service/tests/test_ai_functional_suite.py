"""
ReadAndQues/service/tests/test_ai_functional_suite.py
Comprehensive QA Functional Test Suite for AI Core Components.

Designed from a Senior QA / Tester perspective to validate:
1. Model Routing & Fallback Fault Tolerance (Azure -> OpenAI -> Ollama)
2. Question Generator 4-Node LangGraph Flow (Analyzer, Cleaner, Planner, Verifier, Formatter)
3. Smart Paraphrase AI Tool (Contextual expansion, simplification, edge cases)
4. Contextual Explainer & Token Streaming (Single-word vs sentence breakdown, offline fallback)
5. Grounding & RAG Retrieval (Deterministic chunking, BM25 retrieval, hallucination rejection)
6. AI Platform Tool Policy & Cache Management (Cache hits, error isolation, execution metrics)
"""

from unittest import TestCase
from unittest.mock import MagicMock, Mock, patch

import service.ai_core.tools  # noqa: F401
from service.ai_core.connection.router import ModelRouter, get_llm
from service.ai_core.graphs.ask_article.graph import node_verify_grounding, run_ask_article_flow
from service.ai_core.graphs.explained.graph import run_explained_flow, stream_explained_tokens
from service.ai_core.graphs.question_generator.graph import (
    node_analyzer,
    node_formatter,
    node_question_planner,
    node_text_cleaner,
    node_verifier,
    route_after_verifier,
    run_question_generator_flow,
)
from service.ai_core.graphs.question_generator.schemas import (
    CoreAnalysis,
    ExamOutput,
    QuizItem,
    SemanticAnalysis,
    TextGenre,
    ThemeCategory,
    VerifierFeedback,
)
from service.ai_core.graphs.smart_paraphrase.graph import run_smart_paraphrase_llm
from service.ai_core.grounding import chunk_article_text, retrieve_article_chunks
from service.ai_core.platform import (
    AIToolPolicy,
    ModelGateway,
    get_ai_tool,
)
from service.ai_core.platform.policy import clear_ai_cache, hash_input


class AIFunctionalTestSuite(TestCase):
    """Senior QA Functional Test Suite for AI Core Engine."""

    def setUp(self):
        clear_ai_cache()
        self.sample_passage = (
            "Renewable energy technologies, such as solar photovoltaic panels and wind turbines, "
            "have seen substantial efficiency improvements over the last decade. In particular, "
            "perovskite solar cells promise conversion efficiencies exceeding 30 percent. "
            "However, grid integration and long-duration storage remain significant engineering hurdles."
        )

    def tearDown(self):
        clear_ai_cache()

    # ── 1. Model Router & Resilience Tests ─────────────────────────────────────

    def test_model_router_fallback_from_azure_to_openai(self):
        """QA Test: When primary provider (Azure) fails, router automatically falls back to secondary provider."""
        mock_azure_llm = MagicMock()
        mock_openai_llm = MagicMock()

        providers = {
            "azure": MagicMock(return_value=mock_azure_llm),
            "openai": MagicMock(return_value=mock_openai_llm),
        }

        with patch("service.ai_core.connection.router.get_all_providers", return_value=providers):
            router = ModelRouter(fallback_order=["azure", "openai"])
            result_llm = router.get_llm(temperature=0.2)

            mock_azure_llm.with_fallbacks.assert_called_once_with([mock_openai_llm])
            self.assertEqual(result_llm, mock_azure_llm.with_fallbacks.return_value)

    def test_model_router_exhaustion_raises_runtime_error(self):
        """QA Test: If no providers can be initialized, router raises descriptive RuntimeError."""
        with patch("service.ai_core.connection.router.get_all_providers", return_value={}):
            router = ModelRouter(fallback_order=["azure", "openai"])
            with self.assertRaises(RuntimeError) as ctx:
                router.get_llm(temperature=0.5)
            self.assertIn("No LLM providers could be initialized", str(ctx.exception))

    def test_model_gateway_profile_temperatures(self):
        """QA Test: ModelGateway selects correct temperature profiles ('precise'=0.1, 'creative'=0.7)."""
        with patch("service.ai_core.platform.gateway.default_router.get_llm") as mock_get_llm:
            mock_get_llm.return_value = MagicMock()

            ModelGateway.get_llm("precise")
            mock_get_llm.assert_called_with(temperature=0.1)

            ModelGateway.get_llm("creative")
            mock_get_llm.assert_called_with(temperature=0.7)

            ModelGateway.get_llm("default")
            mock_get_llm.assert_called_with(temperature=0.3)

    # ── 2. Question Generator 4-Node LangGraph Pipeline Tests ───────────────────

    def test_node_analyzer_extracts_themes_and_exam_config(self):
        """QA Test: Analyzer node evaluates text, produces CEFR analysis, and logs token usage."""
        mock_core = CoreAnalysis(
            summary="Renewable energy improvements and perovskite solar cells.",
            central_theme="Renewable energy efficiency",
            irrelevant_snippets=["Advertisement: Buy solar now"],
        )
        mock_analysis = SemanticAnalysis(
            genre=TextGenre.scientific,
            theme=ThemeCategory.environment,
            core=mock_core,
        )

        mock_llm_result = {
            "parsed": mock_analysis,
            "raw": MagicMock(usage_metadata={"input_tokens": 150, "output_tokens": 80}),
        }

        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value.invoke.return_value = mock_llm_result

        with patch("service.ai_core.graphs.question_generator.graph.get_llm", return_value=mock_llm):
            state = {
                "original_text": self.sample_passage,
                "token_log": [],
            }
            output = node_analyzer(state)

            self.assertIn("semantic_analysis", output)
            self.assertEqual(output["semantic_analysis"]["genre"], "scientific")
            self.assertEqual(output["semantic_analysis"]["theme"], "Environment")
            self.assertEqual(output["semantic_analysis"]["core"]["central_theme"], "Renewable energy efficiency")
            self.assertIn("exam_config", output)
            self.assertEqual(len(output["token_log"]), 1)
            self.assertEqual(output["token_log"][0]["node"], "analyzer")
            self.assertEqual(output["token_log"][0]["input_tokens"], 150)
            self.assertEqual(output["retry_count"], 0)

    def test_node_text_cleaner_removes_irrelevant_snippets(self):
        """QA Test: Text cleaner accurately strips noisy snippets identified during semantic analysis."""
        state = {
            "original_text": "Header News. Renewable energy is vital. Footer: Click to subscribe.",
            "semantic_analysis": {
                "irrelevant_snippets": ["Header News. ", " Footer: Click to subscribe."],
            },
        }
        cleaned = node_text_cleaner(state)
        self.assertEqual(cleaned["original_text"], "Renewable energy is vital.")

    def test_node_question_planner_generates_valid_quiz_schema(self):
        """QA Test: Question planner invokes LLM with structured output and builds quizzes."""
        mock_quizzes = [
            QuizItem(
                quiz_type="multiple_choice",
                question="What efficiency level do perovskite solar cells promise?",
                options=["Exceeding 30 percent", "Under 10 percent", "Exactly 50 percent", "Zero percent"],
                correct_answer="Exceeding 30 percent",
                supporting_text="perovskite solar cells promise conversion efficiencies exceeding 30 percent",
                explanation="The passage explicitly notes conversion efficiencies exceeding 30 percent.",
            )
        ]
        mock_exam_output = ExamOutput(quizzes=mock_quizzes)
        mock_llm_result = {
            "parsed": mock_exam_output,
            "raw": MagicMock(usage_metadata={"input_tokens": 200, "output_tokens": 120}),
        }

        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value.invoke.return_value = mock_llm_result

        with patch("service.ai_core.graphs.question_generator.graph.get_llm", return_value=mock_llm):
            state = {
                "original_text": self.sample_passage,
                "semantic_analysis": {"theme": "Environment", "core": {"irrelevant_snippets": []}},
                "exam_config": {"word_count": 50, "total_questions": 1},
                "token_log": [],
            }
            res = node_question_planner(state)
            self.assertEqual(len(res["raw_quizzes"]), 1)
            self.assertEqual(res["raw_quizzes"][0]["correct_answer"], "Exceeding 30 percent")
            self.assertEqual(res["raw_quizzes"][0]["quiz_type"], "multiple_choice")

    def test_node_verifier_approves_accurate_questions(self):
        """QA Test: Verifier passes verified quizzes and flags routing to formatter."""
        mock_feedback = VerifierFeedback(
            passed=True,
            rejected_indices=[],
            reason="All questions are strictly grounded in the passage text.",
        )
        mock_llm_result = {
            "parsed": mock_feedback,
            "raw": MagicMock(usage_metadata={"input_tokens": 120, "output_tokens": 30}),
        }

        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value.invoke.return_value = mock_llm_result

        with patch("service.ai_core.graphs.question_generator.graph.get_llm", return_value=mock_llm):
            state = {
                "original_text": self.sample_passage,
                "raw_quizzes": [{"question": "Q1", "correct_answer": "A"}],
                "retry_count": 0,
                "token_log": [],
            }
            res = node_verifier(state)
            self.assertTrue(res["_verifier_passed"])
            self.assertEqual(len(res["verified_quizzes"]), 1)
            self.assertEqual(route_after_verifier(res), "formatter")

    def test_node_verifier_rejects_hallucinations_and_routes_to_planner(self):
        """QA Test: Verifier filters ungrounded quizzes and routes back to planner for retry."""
        mock_feedback = VerifierFeedback(
            passed=False,
            rejected_indices=[1],
            reason="Question 2 mentions nuclear fusion which is not in the passage.",
        )
        mock_llm_result = {
            "parsed": mock_feedback,
            "raw": MagicMock(usage_metadata={"input_tokens": 120, "output_tokens": 30}),
        }

        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value.invoke.return_value = mock_llm_result

        with patch("service.ai_core.graphs.question_generator.graph.get_llm", return_value=mock_llm):
            state = {
                "original_text": self.sample_passage,
                "raw_quizzes": [
                    {"question": "Q1 (Solar)", "correct_answer": "A"},
                    {"question": "Q2 (Nuclear)", "correct_answer": "B"},
                ],
                "retry_count": 0,
                "token_log": [],
            }
            res = node_verifier(state)
            self.assertFalse(res["_verifier_passed"])
            self.assertEqual(len(res["verified_quizzes"]), 1)
            self.assertEqual(res["verified_quizzes"][0]["question"], "Q1 (Solar)")
            self.assertEqual(res["retry_count"], 1)
            self.assertEqual(route_after_verifier(res), "question_planner")

    def test_node_formatter_assembles_final_exam_payload(self):
        """QA Test: Formatter creates unique exam ID, aggregates token usage, and produces final exam."""
        state = {
            "verified_quizzes": [
                {"question": "Q1", "correct_answer": "Ans1"},
                {"question": "Q2", "correct_answer": "Ans2"},
            ],
            "token_log": [
                {"node": "analyzer", "input_tokens": 100, "output_tokens": 50},
                {"node": "planner", "input_tokens": 200, "output_tokens": 100},
            ],
        }
        res = node_formatter(state)
        exam = res["final_exam"]
        self.assertTrue(exam["exam_id"].startswith("EXAM_"))
        self.assertEqual(exam["total_questions"], 2)
        self.assertEqual(len(exam["quizzes"]), 2)
        self.assertEqual(len(exam["token_usage"]), 2)
        self.assertIn("created_at", exam)

    # ── 3. Smart Paraphrase AI Tool Tests ──────────────────────────────────────

    def test_smart_paraphrase_contextual_expansion_and_simplification(self):
        """QA Test: Smart paraphrase expands target text and returns clear simplification."""
        mock_output = {
            "expanded_text": "Perovskite solar cells promise conversion efficiencies exceeding 30 percent.",
            "paraphrased_text": "New solar cells made of perovskite can turn over 30% of sunlight into power.",
            "explanation": "Replaced 'conversion efficiencies' with 'turn sunlight into power'.",
            "is_valid": True,
        }

        with patch("service.ai_core.graphs.smart_paraphrase.graph.app.invoke", return_value=mock_output):
            result = run_smart_paraphrase_llm(
                highlighted_text="perovskite solar cells promise",
                paragraph_text=self.sample_passage,
            )

            self.assertIn("paraphrased_text", result)
            self.assertIn("30%", result["paraphrased_text"])
            self.assertTrue(result["is_valid"])

    def test_smart_paraphrase_tool_registered_and_executable(self):
        """QA Test: Smart Paraphrase tool is properly registered in AI Platform registry."""
        tool = get_ai_tool("smart_paraphrase")
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "smart_paraphrase")
        self.assertEqual(tool.version, "1.0.0")

        with patch("service.ai_core.graphs.smart_paraphrase.run_smart_paraphrase_llm") as mock_flow:
            mock_flow.return_value = {
                "expanded_text": "expanded sentence",
                "paraphrased_text": "simpler sentence",
            }
            res = tool.run({"highlighted_text": "phrase", "paragraph_text": "full paragraph"})
            self.assertEqual(res.status, "completed")
            self.assertEqual(res.output["paraphrased_text"], "simpler sentence")

    # ── 4. Contextual Explainer & Streaming Tests ──────────────────────────────

    def test_stream_explained_token_generation(self):
        """QA Test: Explainer stream yields tokens for clicked phrase."""
        mock_chunks = [MagicMock(content="**💡 In Simple Words:**\n"), MagicMock(content="Solar power is clean energy.")]
        mock_chain = MagicMock()
        mock_chain.stream.return_value = iter(mock_chunks)

        with patch("service.ai_core.graphs.explained.graph.get_llm") as mock_get_llm:
            mock_get_llm.return_value = MagicMock()
            with patch("service.ai_core.graphs.explained.graph.get_stream_prompt") as mock_prompt:
                mock_prompt.return_value.__or__.return_value = mock_chain

                tokens = list(stream_explained_tokens("solar photovoltaic panels", self.sample_passage))
                self.assertGreater(len(tokens), 0)
                full_text = "".join(tokens)
                self.assertIn("In Simple Words", full_text)

    def test_stream_explained_offline_fallback_generator(self):
        """QA Test: If LLM is offline or times out, explainer produces deterministic high-quality fallback."""
        with patch("service.ai_core.graphs.explained.graph.get_llm", side_effect=ConnectionError("LLM Offline")):
            tokens = list(stream_explained_tokens("perovskite", self.sample_passage))
            full_text = "".join(tokens)
            self.assertIn("In Simple Words", full_text)
            self.assertIn("perovskite", full_text)

    def test_run_explained_flow_structured_output(self):
        """QA Test: Synchronous explained flow returns structured dictionary."""
        with patch("service.ai_core.graphs.explained.graph.stream_explained_tokens", return_value=["Explanation of ", "concept"]):
            res = run_explained_flow("concept", "context text")
            self.assertEqual(res["phrase"], "concept")
            self.assertEqual(res["detailed_explanation"], "Explanation of concept")
            self.assertIn("summary", res)

    # ── 5. Grounding, RAG & Ask Article Tests ──────────────────────────────────

    def test_chunk_article_text_deterministic_hashing(self):
        """QA Test: Article chunking splits paragraphs and generates stable SHA256 hashes."""
        text = "First paragraph on solar.\n\nSecond paragraph on wind turbines."
        chunks = chunk_article_text(text)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0].chunk_id, "chunk_0")
        self.assertTrue(len(chunks[0].content_hash) > 0)
        self.assertEqual(chunks[1].chunk_id, "chunk_1")

    def test_retrieve_article_chunks_relevance(self):
        """QA Test: Chunk retrieval matches relevant paragraphs based on query tokens."""
        text = "Solar panels convert light.\n\nWind turbines use wind kinetic energy.\n\nHydro dams use falling water."
        chunks = chunk_article_text(text)
        matches = retrieve_article_chunks(chunks, "wind turbine kinetic", top_k=1)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].chunk_id, "chunk_1")
        self.assertIn("Wind turbines", matches[0].text)

    def test_node_verify_grounding_rejects_unquoted_claims(self):
        """QA Test: Grounding verification marks hallucinated citation as ungrounded with fallback answer."""
        retrieved = [{"chunk_id": "chunk_0", "text": "Solar energy is expanding."}]
        state = {
            "answer": "Nuclear fusion is powering all cities in 2026.",
            "citation_quote": "Nuclear fusion powers everything.",
            "retrieved_chunks": retrieved,
            "is_grounded": True,
        }
        result = node_verify_grounding(state)
        self.assertFalse(result["is_grounded"])
        self.assertEqual(result["answer"], "not_found_in_article")

    def test_ask_article_tool_ticket_resolution(self):
        """QA Test: Ask Article tool executes RAG pipeline and returns grounded ticket."""
        tool = get_ai_tool("ask_article")
        self.assertIsNotNone(tool)

        with patch("service.ai_core.tools.ask_article_tool.run_ask_article_flow") as mock_flow:
            mock_flow.return_value = {
                "ticket_id": "TKT-TEST-999",
                "question": "What is the solar efficiency?",
                "answer": "Over 30 percent with perovskite cells.",
                "citation_quote": "efficiencies exceeding 30 percent",
                "status": "RESOLVED",
                "timestamp": "12:00:00",
                "is_grounded": True,
            }
            res = tool.run({"article_text": self.sample_passage, "question": "What is the solar efficiency?"})
            self.assertEqual(res.status, "completed")
            self.assertEqual(res.output["ticket_id"], "TKT-TEST-999")
            self.assertTrue(res.output["is_grounded"])

    # ── 6. AI Policy & Execution Engine Tests ──────────────────────────────────

    def test_ai_tool_policy_caching_mechanism(self):
        """QA Test: Policy caches execution output on identical input, bypassing duplicate LLM calls."""
        call_counter = {"count": 0}

        def mock_llm_execution():
            call_counter["count"] += 1
            return {"result": f"processed_{call_counter['count']}"}

        input_payload = {"text": "identical query", "param": 42}

        res1 = AIToolPolicy.execute(
            tool_name="test_tool",
            version="1.0.0",
            func=mock_llm_execution,
            input_data=input_payload,
            use_cache=True,
        )
        self.assertEqual(call_counter["count"], 1)
        self.assertEqual(res1.output["result"], "processed_1")

        res2 = AIToolPolicy.execute(
            tool_name="test_tool",
            version="1.0.0",
            func=mock_llm_execution,
            input_data=input_payload,
            use_cache=True,
        )
        self.assertEqual(call_counter["count"], 1)
        self.assertEqual(res2.output["result"], "processed_1")
        self.assertEqual(res2.duration_ms, 0.0)

    def test_ai_tool_policy_failure_isolation(self):
        """QA Test: Tool exceptions are trapped and returned as failed result with error detail."""
        def broken_func():
            raise ValueError("Upstream AI model rate limit exceeded")

        res = AIToolPolicy.execute(
            tool_name="broken_tool",
            version="1.0.0",
            func=broken_func,
            input_data={"test": "crash"},
            use_cache=False,
        )
        self.assertEqual(res.status, "failed")
        self.assertIn("rate limit exceeded", res.error)
        self.assertGreaterEqual(res.duration_ms, 0.0)
