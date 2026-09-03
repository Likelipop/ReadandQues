"""
ReadAndQues/service/tests/test_student_architecture.py
Comprehensive QA Test Suite for Simplified, Student-Friendly Architecture.

Validates:
1. Pure Azure OpenAI LLM Connection & Temperature Controls
2. Direct AI Graph Flows (Explainer & Question Generator)
3. MongoDB Storage Layer (Articles, Exams, Activity, Pipeline)
4. MinIO S3 Object Storage Layer (Bronze, Silver, Gold Tiers)
5. ChromaDB Vector Store Operations
6. BM25 Lexical Search & spaCy NLP Preprocessing
7. End-to-End ETL and Service Workflows
"""

import json
from datetime import UTC, datetime
from io import BytesIO
from unittest import TestCase
from unittest.mock import MagicMock, Mock, patch

from minio.error import S3Error
from pymongo.errors import ConnectionFailure, PyMongoError

import service.infrastructure.bm25.connection as bm25_conn
import service.infrastructure.bm25.index as bm25_idx
import service.infrastructure.bm25.text_processing as bm25_nlp
import service.infrastructure.chroma.vector_store as vector_store
import service.infrastructure.minio.object_store as minio_store
import service.infrastructure.mongo.activity_store as activity_store
import service.infrastructure.mongo.article_store as article_store
import service.infrastructure.mongo.exam_store as exam_store
from ai_service.connection import get_azure_llm, get_llm
from ai_service.explainer.explainer import run_explained_flow, stream_explained_tokens
from ai_service.quiz_generator.generator import run_question_generator_flow
from ai_service.quiz_generator.schemas import ExamOutput, QuizItem, SemanticAnalysis
from service.pipelines import ingest_and_enrich_article
from service.services import explain_phrase


class StudentArchitectureTests(TestCase):
    """QA Test Suite verifying all student-friendly refactored units."""

    def setUp(self):
        self.sample_text = (
            "Perovskite solar cells promise conversion efficiencies exceeding 30 percent. "
            "Unlike traditional silicon wafers, perovskite thin films can be printed on flexible substrates at low temperatures. "
            "However, long-term stability against moisture and thermal degradation remains a major commercialization barrier."
        )

    # ── 1. Azure OpenAI Connection ────────────────────────────────────────────

    def test_azure_llm_configuration(self):
        """Test that Azure LLM is created with correct environment variables and parameters."""
        with patch.dict(
            "os.environ",
            {
                "AZURE_OPENAI_API_KEY": "dummy-azure-key",
                "AZURE_OPENAI_ENDPOINT": "https://test.services.ai.azure.com",
                "AZURE_DEPLOYMENT_NAME": "gpt-4o-mini",
            },
        ):
            llm = get_azure_llm(temperature=0.5)
            self.assertEqual(llm.deployment_name, "gpt-4o-mini")
            self.assertEqual(llm.temperature, 0.5)

    def test_get_llm_delegates_to_azure(self):
        """Test that the global get_llm() helper delegates to Azure LLM."""
        with patch.dict(
            "os.environ",
            {
                "AZURE_OPENAI_API_KEY": "dummy-azure-key",
                "AZURE_OPENAI_ENDPOINT": "https://test.services.ai.azure.com",
                "AZURE_DEPLOYMENT_NAME": "gpt-4o-mini",
            },
        ):
            llm = get_llm(temperature=0.2)
            self.assertEqual(llm.temperature, 0.2)

    def test_azure_llm_missing_api_key(self):
        """Test that missing API key raises clear ValueError."""
        with patch.dict("os.environ", {"AZURE_OPENAI_API_KEY": ""}):
            with self.assertRaises(ValueError) as ctx:
                get_azure_llm()
            self.assertIn("Missing AZURE_OPENAI_API_KEY", str(ctx.exception))

    # ── 2. Direct AI Flows ───────────────────────────────────────────────────

    def test_direct_question_generator_flow(self):
        """Test that run_question_generator_flow invokes LLM and formats exam schema."""
        mock_quizzes = [
            QuizItem(
                quiz_type="multiple_choice",
                question="What efficiency level do perovskite solar cells promise?",
                options=["Exceeding 30 percent", "Under 10 percent", "50 percent", "0 percent"],
                correct_answer="Exceeding 30 percent",
                supporting_text="exceeding 30 percent",
                explanation="The text states over 30 percent.",
            )
        ]
        mock_output = ExamOutput(
            quizzes=mock_quizzes,
            semantic_analysis=SemanticAnalysis(genre="academic", theme="Science", summary="Summary text"),
        )
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value.invoke.return_value = mock_output

        with patch("ai_service.quiz_generator.generator.get_llm", return_value=mock_llm):
            result = run_question_generator_flow(self.sample_text)
            self.assertIn("questions", result)
            self.assertEqual(len(result["questions"]), 1)
            self.assertEqual(result["final_exam"]["total_questions"], 1)

    def test_direct_explained_flow(self):
        """Test that run_explained_flow aggregates streamed explainer tokens."""
        with patch(
            "ai_service.explainer.explainer.stream_explained_tokens",
            return_value=iter(["**💡 In Simple Words:**\n", "Solar cells generate clean electricity."]),
        ):
            result = run_explained_flow("solar cells", paragraph_context=self.sample_text)
            self.assertEqual(result["phrase"], "solar cells")
            self.assertIn("Solar cells generate", result["detailed_explanation"])

    # ── 3. MongoDB Storage Layer ──────────────────────────────────────────────

    def test_mongo_article_store_operations(self):
        """Test article_store Gold CRUD operations with mocked collection."""
        mock_coll = MagicMock()
        mock_coll.find_one.return_value = {"article_id": "art-1", "title": "Test Article", "source": "Nature"}
        mock_coll.find.return_value.sort.return_value.skip.return_value.limit.return_value = [{"article_id": "art-1"}]
        mock_coll.count_documents.return_value = 1
        mock_coll.delete_one.return_value.deleted_count = 1

        with patch("service.infrastructure.mongo.article_store._gold_coll", return_value=mock_coll):
            self.assertIsNotNone(article_store.get_gold_content("art-1"))
            self.assertIsNotNone(article_store.get_gold_content_by_url("https://example.com"))
            self.assertEqual(len(article_store.list_gold_articles()), 1)
            self.assertEqual(article_store.count_gold_articles(), 1)
            self.assertTrue(article_store.delete_gold_content("art-1"))

    def test_mongo_article_store_handles_pymongo_error(self):
        """Test that article_store handles PyMongoError gracefully."""
        mock_coll = MagicMock()
        mock_coll.find_one.side_effect = ConnectionFailure("MongoDB unreachable")

        with patch("service.infrastructure.mongo.article_store._gold_coll", return_value=mock_coll):
            doc = article_store.get_gold_content("art-err")
            self.assertIsNone(doc)

    def test_mongo_exam_store_operations(self):
        """Test exam_store save, get, list, and delete operations."""
        mock_coll = MagicMock()
        mock_coll.update_one.return_value.acknowledged = True
        mock_coll.find_one.return_value = {"article_id": "art-1", "theme": "Technology"}
        mock_coll.find.return_value.sort.return_value.limit.return_value = [{"article_id": "art-1"}]
        mock_coll.delete_one.return_value.deleted_count = 1

        with patch("service.infrastructure.mongo.exam_store._coll", return_value=mock_coll):
            self.assertTrue(exam_store.save_exam("art-1", {"title": "Test Exam"}))
            self.assertIsNotNone(exam_store.get_exam("art-1"))
            self.assertEqual(len(exam_store.list_exams(theme="Technology")), 1)
            self.assertTrue(exam_store.delete_exam("art-1"))

    def test_mongo_activity_store_operations(self):
        """Test activity_store reading history, user highlights, and vocab tracking."""
        mock_coll = MagicMock()
        mock_coll.update_one.return_value.acknowledged = True
        mock_coll.insert_one.return_value.acknowledged = True
        mock_coll.find.return_value.sort.return_value.limit.return_value = [{"word": "perovskite"}]

        with patch("service.infrastructure.mongo.activity_store.get_collection", return_value=mock_coll):
            self.assertTrue(activity_store.log_reading_session(user_id=1, article_id="art-1", duration_sec=120, completion_rate=1.0))
            self.assertTrue(activity_store.add_highlight(user_id=1, article_id="art-1", highlighted_text="solar cells"))
            self.assertTrue(activity_store.track_vocab(user_id=1, word="perovskite", article_id="art-1"))
            self.assertEqual(len(activity_store.get_daily_vocab_for_user(user_id=1)), 1)
            self.assertTrue(activity_store.delete_article_activity("art-1"))

    def test_mongo_gold_content_save(self):
        """Test article_store save_gold_content and delete_gold_content operations."""
        mock_coll = MagicMock()
        mock_coll.update_one.return_value.acknowledged = True
        mock_coll.delete_one.return_value.deleted_count = 1

        with patch("service.infrastructure.mongo.article_store._gold_coll", return_value=mock_coll):
            doc = {"article_id": "art-1", "title": "Gold Title", "original_text": "Sample text"}
            self.assertTrue(article_store.save_gold_content(doc))
            self.assertTrue(article_store.delete_gold_content("art-1"))


    # ── 4. MinIO S3 Storage Layer ─────────────────────────────────────────────

    def test_minio_object_store_roundtrip(self):
        """Test MinIO Bronze, Silver, Gold saving and reading."""
        fake_store = {}

        def mock_put_object(bucket_name, object_name, data, length, content_type):
            fake_store[f"{bucket_name}/{object_name}"] = data.getvalue()
            return MagicMock()

        def mock_get_object(bucket_name, object_name):
            key = f"{bucket_name}/{object_name}"
            if key not in fake_store:
                err_resp = MagicMock()
                raise S3Error("NoSuchKey", "The specified key does not exist.", "resource", "reqid", "hostid", err_resp)
            mock_res = MagicMock()
            mock_res.read.return_value = fake_store[key]
            return mock_res

        with (
            patch("service.infrastructure.minio.object_store.client.put_object", side_effect=mock_put_object),
            patch("service.infrastructure.minio.object_store.client.get_object", side_effect=mock_get_object),
            patch("service.infrastructure.minio.object_store.client.remove_object"),
        ):
            # Bronze HTML
            self.assertTrue(minio_store.save_bronze_html("art-100", "<html><body>Article content</body></html>"))

            # Silver Clean JSON
            clean_payload = {"title": "Quantum Physics", "cleaned_text": "Clean body"}
            self.assertTrue(minio_store.save_silver_clean("art-100", clean_payload))
            read_clean = minio_store.read_silver_clean("art-100")
            self.assertEqual(read_clean["title"], "Quantum Physics")

            # Gold Enriched JSON
            enriched_payload = {"title": "Quantum Physics", "has_quiz": True}
            self.assertTrue(minio_store.save_gold_enriched("art-100", enriched_payload))
            read_gold = minio_store.read_gold_enriched("art-100")
            self.assertEqual(read_gold["has_quiz"], True)

            # Cleanup
            self.assertTrue(minio_store.delete_article_objects("art-100"))

    # ── 5. ChromaDB Vector Store Operations ───────────────────────────────────

    def test_chroma_vector_store_operations(self):
        """Test ChromaDB article vector upsert, search, and deletion."""
        mock_articles = MagicMock()
        mock_articles.query.return_value = {
            "ids": [["art-2", "art-3"]],
            "distances": [[0.1, 0.3]],
            "metadatas": [[{"title": "Title 2"}, {"title": "Title 3"}]],
        }

        mock_news = MagicMock()
        mock_news.query.return_value = {
            "ids": [["chunk_1"]],
            "documents": [["Chunk text"]],
            "metadatas": [[{"theme": "Technology"}]],
            "distances": [[0.2]],
        }

        with (
            patch("service.infrastructure.chroma.vector_store.articles_collection", mock_articles),
            patch("service.infrastructure.chroma.vector_store.news_chunks_collection", mock_news),
        ):
            self.assertTrue(vector_store.add_article_vector("art-1", "Summary", "Title", "https://url.com"))
            related = vector_store.query_related_chroma_ids("Summary", exclude_id="art-1")
            self.assertIn("art-2", related)

            search_res = vector_store.search_by_text("Query text", limit=2)
            self.assertEqual(len(search_res), 2)

            chunks_res = vector_store.vector_search_chunks("Query chunk", limit=1)
            self.assertEqual(len(chunks_res), 1)

            self.assertTrue(vector_store.delete_article_chunks("art-1"))

    # ── 6. BM25 Lexical Search & spaCy NLP ────────────────────────────────────

    def test_spacy_nlp_tokenization_and_cleaning(self):
        """Test spaCy clean_text and tokenize_and_lemmatize preserving short valid words."""
        raw_text = "The solar cells &amp; AI models run at 30% efficiency in US."
        cleaned = bm25_nlp.clean_text(raw_text)
        self.assertNotIn("&amp;", cleaned)
        self.assertNotIn("%", cleaned)

        tokens = bm25_nlp.tokenize_and_lemmatize(cleaned)
        self.assertIsInstance(tokens, list)
        self.assertIn("solar", tokens)
        self.assertIn("cell", tokens)  # Lemmatized from 'cells'
        self.assertIn("model", tokens)  # Lemmatized from 'models'

    def test_bm25_marker_extraction_and_search(self):
        """Test BM25 highlight marker extraction and search."""
        markdown_text = "==quantum entanglement== is fundamental to ==quantum computing==."
        extracted = bm25_idx.extract_markers_text(markdown_text)
        self.assertEqual(extracted, "quantum entanglement quantum computing")

        with patch("service.infrastructure.bm25.index.get_index") as mock_get_idx:
            mock_bm25 = MagicMock()
            mock_bm25.get_scores.return_value = [2.5, 0.0]
            mock_get_idx.return_value = (mock_bm25, ["art-1", "art-2"])

            results = bm25_idx.search_bm25(["quantum", "computing"], n=5)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["id"], "art-1")
            self.assertEqual(results[0]["score"], 2.5)

    # ── 7. End-to-End Pipeline & Service Helper ───────────────────────────────

    def test_pipeline_and_explain_phrase_service(self):
        """Test full ETL ingestion flow and explain_phrase service wrapper."""
        mock_crawl = {
            "success": True,
            "title": "Quantum Physics",
            "author": "Dr. Planck",
            "raw_text": "Quantum computers leverage qubits.",
            "html_content": "<p>Quantum computers leverage qubits.</p>",
            "source_name": "ScienceDaily",
            "word_count": 5,
        }
        mock_ai_result = {
            "keywords": ["Science"],
            "summary": "Quantum summary",
            "questions": [{"question": "Q1", "correct_answer": "A"}],
        }

        with (
            patch("service.pipelines.trafilatura.fetch_url", return_value="<html>Sample</html>"),
            patch("service.pipelines.trafilatura.extract", return_value="Quantum computers leverage qubits for fast computation. " * 10),
            patch("service.pipelines.object_store.save_silver_clean"),
            patch("service.pipelines.article_store.save_gold_content", return_value=True),
            patch("service.pipelines.generate_quiz", return_value=mock_ai_result),
            patch("service.pipelines.exam_store.save_exam"),
            patch("service.pipelines.index_article", return_value=True),
        ):
            res = ingest_and_enrich_article(article_id="art-pipeline-1", url="https://example.com/quantum")
            self.assertEqual(res["status"], "completed")

        with patch(
            "ai_service.interface.explain_phrase",
            return_value={
                "summary": "Quantum particle explanation",
                "detailed_explanation": "Detailed physics concept",
                "simplified_version": "simple qubit",
                "key_terms": ["qubit"],
            },
        ):
            exp_res = explain_phrase("art-1", "qubit", paragraph_context="Quantum computer uses qubit.")
            self.assertEqual(exp_res["article_id"], "art-1")
            self.assertEqual(exp_res["phrase"], "qubit")
            self.assertEqual(exp_res["summary"], "Quantum particle explanation")
