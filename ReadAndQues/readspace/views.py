import json
import logging
from datetime import datetime

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from django.core.paginator import Paginator

from .decorators import api_error_handler, rate_limit
from .utils import consume_user_star
import service.services as services
import service.selectors as selectors

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
        from accounts.models import UserProfile
        from django.db import transaction
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
@csrf_exempt
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
@csrf_exempt
@api_error_handler
def submit_exam_attempt(request, pk):
    data = json.loads(request.body)
    score = data.get("score", 0)
    total_questions = data.get("total_questions", 0)
    answers = data.get("answers", {})
    highlighted_markdown = data.get("highlighted_markdown", "")
    elapsed_time = data.get("elapsed_time", 0)
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
@csrf_exempt
@api_error_handler
def smart_paraphrase_api(request, pk: str):
    data = json.loads(request.body)
    paragraph_text = data.get("paragraph_text", "").strip()
    start_idx = data.get("start_index", 0)
    end_idx = data.get("end_index", 0)

    if not paragraph_text:
        return JsonResponse({"status": "error", "message": "Missing paragraph_text"}, status=400)

    res = services.smart_paraphrase(
        article_id=pk,
        paragraph_text=paragraph_text,
        user_start_index=start_idx,
        user_end_index=end_idx,
    )

    return JsonResponse({
        "status": "success",
        "paraphrased_text": res.get("paraphrased_text"),
        "explanation": res.get("explanation"),
    })


@require_POST
@login_required(login_url='/login/')
@csrf_exempt
@api_error_handler
def save_markers_api(request, pk: str):
    data = json.loads(request.body)
    highlighted_markdown = data.get("highlighted_markdown", "")

    services.save_user_highlights(
        user_id=request.user.id,
        article_id=pk,
        highlights=highlighted_markdown,
    )
    return JsonResponse({"status": "success"})


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


@csrf_exempt
@api_error_handler
def run_ai_tool_api(request):
    """Generic AI Tool gateway endpoint."""
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=405)
    try:
        body = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    question = body.get("question") or body.get("input_data", {}).get("question", "")
    article_id = body.get("article_id")

    res = services.ask_rag_question(question=question, article_id=article_id)
    return JsonResponse(res)
