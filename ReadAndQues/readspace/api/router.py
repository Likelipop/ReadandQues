"""
Typed Django Ninja API Router for ReadAndQues.
Provides OpenAPI / Swagger docs at /readspace/api/docs
"""

import logging
from typing import Any

from django.http import HttpRequest
from ninja import NinjaAPI, Router
from ninja.errors import HttpError
from ninja.security import django_auth

import service.selectors as selectors
import service.services as services
from service.passage_proof_service import get_passage_proof

from .schemas import (
    ExamSubmitIn,
    ExamSubmitOut,
    GenericAiToolIn,
    PassageProofOut,
    SaveMarkersIn,
    SearchResponseOut,
    SmartParaphraseIn,
    SmartParaphraseOut,
    StatusResponse,
)

logger = logging.getLogger(__name__)

api = NinjaAPI(
    title="ReadAndQues REST API",
    version="1.0.0",
    description="Interactive IELTS Reading & RAG Intelligence Endpoints",
    urls_namespace="readspace_ninja",
)

router = Router()


# ── Status & Ingestion Endpoints ──────────────────────────────────────────────

@router.get("/status/{pk}/", response=dict[str, Any], summary="Get Article Pipeline Status")
def get_article_status(request: HttpRequest, pk: str):
    """Poll the ingestion and AI generation status for a specific article."""
    payload = selectors.get_article_status(pk)
    return payload


@router.post("/trigger-quiz/{pk}/", response=StatusResponse, auth=django_auth, summary="Trigger Quiz Generation")
def trigger_quiz(request: HttpRequest, pk: str):
    """Trigger background AI quiz generation for an existing article."""
    res = services.trigger_quiz_generation(pk)
    if res.get("status") == "error":
        raise HttpError(404, res.get("message", "Article not found"))
    return {"status": "processing"}


# ── Interactive Reading & Practice Endpoints ─────────────────────────────────

@router.post("/{pk}/submit/", response=ExamSubmitOut, auth=django_auth, summary="Submit Quiz Attempt")
def submit_exam_attempt(request: HttpRequest, pk: str, data: ExamSubmitIn):
    """Submit user quiz answers, record performance log and calculate topic proficiencies."""
    user_id = request.user.id
    res = services.submit_exam_attempt(
        user_id=user_id,
        article_id=pk,
        score=data.score,
        total_questions=data.total_questions,
        answers=data.answers,
        highlighted_markdown=data.highlighted_markdown,
        elapsed_time=data.elapsed_time,
    )
    related = selectors.get_related_articles(pk, limit=5)
    return {
        "status": "success",
        "id": str(res.get("attempt_id", "")),
        "related_articles": related,
    }


@router.post("/{pk}/smart_paraphrase/", response=SmartParaphraseOut, auth=django_auth, summary="Smart Paraphrase Selection")
def smart_paraphrase(request: HttpRequest, pk: str, data: SmartParaphraseIn):
    """Generate CEFR-level explanation and contextual paraphrase for selected text."""
    if not data.paragraph_text.strip():
        raise HttpError(400, "Missing paragraph_text")

    res = services.smart_paraphrase(
        article_id=pk,
        paragraph_text=data.paragraph_text.strip(),
        user_start_index=data.start_index,
        user_end_index=data.end_index,
    )
    return {
        "status": "success",
        "paraphrased_text": res.get("paraphrased_text"),
        "explanation": res.get("explanation"),
    }


@router.post("/{pk}/save_markers/", response=StatusResponse, auth=django_auth, summary="Save Workspace Highlights")
def save_markers(request: HttpRequest, pk: str, data: SaveMarkersIn):
    """Save user text highlights to document storage."""
    services.save_user_highlights(
        user_id=request.user.id,
        article_id=pk,
        highlights=data.highlighted_markdown,
    )
    return {"status": "success"}


@router.get("/{pk}/proof/{idx}/", response=PassageProofOut, summary="Get Passage Grounding Proof")
def get_passage_proof_endpoint(request: HttpRequest, pk: str, idx: int):
    """Retrieve grounded proof excerpt and confidence score for a question."""
    proof = get_passage_proof(article_id=pk, question_idx=idx)
    if not proof:
        raise HttpError(404, "Proof not found")
    return {"status": "success", "proof": proof}


# ── Search & AI Tool Endpoints ───────────────────────────────────────────────

@router.get("/search/keyword/", response=SearchResponseOut, summary="BM25 Keyword Search")
def search_keyword(request: HttpRequest, q: str):
    """Perform BM25 tokenized keyword search across articles."""
    if not q.strip():
        raise HttpError(400, "Missing search query")
    results = selectors.search_articles_keyword(q.strip())
    return {"status": "success", "results": results}


@router.get("/search/semantic/", response=SearchResponseOut, summary="Semantic Vector Search")
def search_semantic(request: HttpRequest, q: str):
    """Perform dense vector embedding search via ChromaDB."""
    if not q.strip():
        raise HttpError(400, "Missing search query")
    results = selectors.search_articles_semantic(q.strip())
    return {"status": "success", "results": results}


@router.post("/ai/tool/run/", response=dict[str, Any], summary="Generic AI Tool Gateway")
def run_ai_tool(request: HttpRequest, data: GenericAiToolIn):
    """Gateway endpoint for invoking RAG tool questions."""
    question = data.question or (data.input_data.get("question") if data.input_data else "") or ""
    if not question.strip():
        raise HttpError(400, "Missing question in request")
    res = services.ask_rag_question(question=question, article_id=data.article_id)
    return res


api.add_router("/", router)
