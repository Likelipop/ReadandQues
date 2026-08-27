import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST

import service.selectors as selectors
import service.services as services

from .decorators import api_error_handler, rate_limit
from .utils import consume_user_star

logger = logging.getLogger(__name__)


# ── Core Reading Workspace Views ──────────────────────────────────────────────

@require_GET
@login_required(login_url='/login/')
@never_cache
def readspace_view(request, pk):
    """Displays the article in the 3-column Reading Space layout."""
    doc = selectors.get_article_detail(pk)
    if not doc:
        messages.error(request, "Requested article not found!")
        return redirect("home")

    related = selectors.get_related_articles(pk, limit=5)
    return render(
        request,
        "readspace/layout.html",
        {"article": doc, "related_articles": related},
    )


@require_http_methods(["POST"])
@login_required(login_url='/login/')
@rate_limit(requests=5, timeout=60)
def import_article_view(request):
    """Import article URL and trigger background ingestion."""
    url = request.POST.get("url", "").strip()
    user_id = request.user.id if request.user.is_authenticated else 0

    with consume_user_star(request.user):
        result = services.import_article(url, user_id)

    inserted_id = result.get("article_id")
    is_new = result.get("is_new", False)

    if request.user.is_authenticated:
        from django.db import transaction

        from accounts.models import UserProfile
        try:
            with transaction.atomic():
                profile = UserProfile.objects.select_for_update().get(user=request.user)
                if not is_new:
                    profile.stars += 1
                else:
                    profile.total_articles_imported += 1
                profile.save()
        except Exception as e:
            logger.error(f"Error updating user stats on import: {e}")

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"status": "started", "id": inserted_id})

    return redirect("readspace:readspace_detail", pk=inserted_id)


@require_POST
@login_required(login_url='/login/')
@api_error_handler
def trigger_quiz(request, pk):
    res = services.trigger_quiz_generation(pk)
    if res.get("status") == "error":
        return JsonResponse({"status": "error", "message": res.get("message")}, status=404)
    return JsonResponse({"status": "processing"})


@require_GET
@api_error_handler
def article_status(request, pk):
    payload = selectors.get_article_status(pk)
    return JsonResponse(payload)


@require_GET
@never_cache
def all_tests_view(request):
    """Lists completed tests with theme, genre, and keyword search filters."""
    query = request.GET.get("q", "").strip()
    selected_theme = request.GET.get("theme", "All")
    selected_genre = request.GET.get("genre", "All")
    user_id = request.user.id if request.user.is_authenticated else None

    if query:
        articles = selectors.search_articles_keyword(query, limit=50)
    else:
        res = selectors.list_completed_articles(theme=selected_theme, genre=selected_genre, limit=100)
        articles = res.get("articles", [])

    attempted_ids = selectors.get_user_attempted_ids(user_id)
    for art in articles:
        aid = art.get("article_id") or art.get("id")
        art["has_attempted"] = aid in attempted_ids

    themes = selectors.get_theme_choices()
    genres = selectors.get_genre_choices()

    paginator = Paginator(articles, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "readspace/all_tests.html",
        {
            "page_obj": page_obj,
            "themes": themes,
            "genres": genres,
            "selected_theme": selected_theme,
            "selected_genre": selected_genre,
            "search_query": query,
        },
    )


@require_POST
@login_required(login_url='/login/')
@api_error_handler
def submit_exam_attempt(request, pk):
    data = json.loads(request.body)
    score = data.get("score", 0)
    total_questions = data.get("total_questions", 0)
    answers = data.get("answers", {})
    highlighted_markdown = data.get("highlighted_markdown", "")
    elapsed_time = data.get("elapsed_time") or data.get("time_taken_seconds", 0)
    user_id = request.user.id

    res = services.submit_exam_attempt(
        user_id=user_id,
        article_id=pk,
        score=score,
        total_questions=total_questions,
        answers=answers,
        highlighted_markdown=highlighted_markdown,
        elapsed_time=elapsed_time,
    )

    related = selectors.get_related_articles(pk, limit=5)
    return JsonResponse({"status": "success", "id": res.get("attempt_id"), "related_articles": related})



@require_POST
@login_required(login_url='/login/')
@api_error_handler
def save_markers_api(request, pk: str):
    data = json.loads(request.body)
    highlighted_markdown = data.get("highlighted_markdown") or data.get("highlights", "")

    services.save_user_highlights(
        user_id=request.user.id,
        article_id=pk,
        highlighted_text=highlighted_markdown,
    )
    return JsonResponse({"status": "success"})


@require_POST
@csrf_exempt
def rag_stream_api(request):
    """Server-Sent Events (SSE) streaming endpoint for RAG Study Buddy responses."""
    import time

    from django.http import StreamingHttpResponse

    try:
        body = json.loads(request.body.decode("utf-8"))
    except Exception:
        body = {}

    question = body.get("question", "").strip()
    article_id = body.get("article_id")

    if not question:
        return JsonResponse({"status": "error", "message": "Question required"}, status=400)

    res = services.ask_rag_question(question=question, article_id=article_id)
    answer_text = res.get("answer", "")
    citations = res.get("citations", [])

    def event_stream():
        # Stream metadata first
        yield f"data: {json.dumps({'type': 'metadata', 'citations': citations})}\n\n"
        time.sleep(0.05)

        # Stream words word-by-word (ChatGPT style)
        words = answer_text.split(" ")
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            payload = json.dumps({"type": "delta", "text": chunk})
            yield f"data: {payload}\n\n"
            time.sleep(0.02)

        yield "data: [DONE]\n\n"

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


@csrf_exempt
@require_POST
def explain_stream_api(request, pk: str | None = None):
    """Stream token-by-token explanation for clicked markdown phrase/sentence."""
    try:
        body = json.loads(request.body.decode("utf-8")) if request.body else {}
    except Exception:
        body = {}

    phrase = body.get("phrase", "").strip()
    paragraph_context = body.get("paragraph_context", "").strip()

    if not phrase:
        return JsonResponse({"status": "error", "message": "Missing phrase"}, status=400)

    from service.ai_core.graphs import stream_explained_tokens

    def event_stream():
        is_term = len(phrase.split()) <= 2
        yield f"data: {json.dumps({'type': 'metadata', 'phrase': phrase, 'is_term': is_term})}\n\n"
        for chunk in stream_explained_tokens(phrase=phrase, paragraph_context=paragraph_context):
            payload = json.dumps({"type": "delta", "text": chunk})
            yield f"data: {payload}\n\n"
        yield "data: [DONE]\n\n"

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response



@require_GET
@api_error_handler
def passage_proof_api(request, pk: str, idx: int):
    from service.passage_proof_service import get_passage_proof
    proof = get_passage_proof(article_id=pk, question_idx=idx)
    if not proof:
        return JsonResponse({"status": "error", "message": "Proof not found"}, status=404)
    return JsonResponse({"status": "success", "proof": proof})


@require_GET
@api_error_handler
def search_bm25_api(request):
    query = request.GET.get("q", "").strip()
    if not query:
        return JsonResponse({"status": "error", "message": "Missing query"}, status=400)

    results = selectors.search_articles_keyword(query)
    return JsonResponse({"status": "success", "results": results})


@require_GET
@api_error_handler
def search_semantic_api(request):
    query = request.GET.get("q", "").strip()
    if not query:
        return JsonResponse({"status": "error", "message": "Missing query"}, status=400)

    results = selectors.search_articles_semantic(query)
    return JsonResponse({"status": "success", "results": results})


@api_error_handler
def run_ai_tool_api(request):
    """Generic AI Tool gateway endpoint."""
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=405)
    try:
        body = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    question = body.get("question") or (body.get("input_data", {}).get("question") if isinstance(body.get("input_data"), dict) else "") or ""
    article_id = body.get("article_id")

    res = services.ask_rag_question(question=question, article_id=article_id)
    answer = res.get("answer", "")
    citations = res.get("citations", [])
    first_quote = citations[0].get("quote", "") if citations and isinstance(citations[0], dict) else ""

    return JsonResponse({
        "status": "success",
        "answer": answer,
        "citations": citations,
        "output": {
            "answer": answer,
            "citation_quote": first_quote,
            "status": "RESOLVED",
        },
    })
