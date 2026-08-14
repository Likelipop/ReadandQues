import json
import hashlib
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

from .models import AttemptMongoModel
from .decorators import api_error_handler, rate_limit
from .utils import consume_user_star
from .services import (
    get_article_detail,
    import_article,
    trigger_article_quiz,
    get_article_status_payload,
    get_all_tests,
    save_attempt,
    get_smart_paraphrase,
    search_bm25_articles,
    search_semantic_articles,
)

logger = logging.getLogger(__name__)


# --- Core Views ---

@require_GET
@login_required(login_url='/login/')
@never_cache
def readspace_view(request, pk):
    """Displays the article in the 3-column Reading Space layout."""
    doc, related_articles = get_article_detail(pk)
    if not doc:
        messages.error(request, "Requested article not found!")
        return redirect("home")

    return render(
        request,
        "readspace/layout.html",
        {"article": doc, "related_articles": related_articles},
    )


@require_http_methods(["POST"])
@login_required(login_url='/login/')
@rate_limit(requests=5, timeout=60)
def import_article_view(request):
    """
    Validates input URL, checks rate limit, deduplicates, and kicks off AI exam pipeline.
    """
    url = request.POST.get("url", "").strip()
    user_id = request.user.id if request.user.is_authenticated else 0

    with consume_user_star(request.user):
        inserted_id, is_reused = import_article(url, user_id)

    if request.user.is_authenticated:
        from .utils import UserProfile
        from django.db import transaction
        try:
            with transaction.atomic():
                profile = UserProfile.objects.select_for_update().get(user=request.user)
                if is_reused:
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
@api_error_handler
def trigger_quiz(request, pk):
    success = trigger_article_quiz(pk)
    if not success:
        return JsonResponse({"status": "error", "message": "Article not found"}, status=404)
        
    return JsonResponse({"status": "processing"})


@require_GET
@api_error_handler
def article_status(request, pk):
    payload = get_article_status_payload(pk)
    if payload is None:
        return JsonResponse({"status": "error", "message": "Article not found."}, status=404)

    return JsonResponse(payload)


def is_valid_url(text: str) -> bool:
    if not text:
        return False
    t = text.strip()
    return (
        t.startswith("http://")
        or t.startswith("https://")
        or t.startswith("www.")
        or ("." in t and "/" in t and not t.startswith(" "))
    )


@require_GET
@never_cache
def all_tests_view(request):
    """Lists completed tests with category, genre, and search filtering."""
    query = request.GET.get("q", "").strip()

    # If user pasted a news/paper URL into search bar, import and redirect to Reading Space!
    if query and is_valid_url(query):
        url = query if (query.startswith("http://") or query.startswith("https://")) else f"https://{query}"
        user_id = request.user.id if request.user.is_authenticated else 0
        try:
            article_id, _ = import_article(url, user_id=user_id)
            if article_id:
                return redirect("readspace:readspace_detail", pk=article_id)
        except Exception as exc:
            logger.error(f"Failed to auto-import URL from search bar: {exc}")
            messages.error(request, f"Could not import article from URL: {url}")

    selected_theme = request.GET.get("theme", "All")
    selected_genre = request.GET.get("genre", "All")
    user_id = request.user.id if request.user.is_authenticated else None

    try:
        articles = get_all_tests(theme=selected_theme, genre=selected_genre, user_id=user_id, search_query=query)
    except Exception as exc:
        logger.exception("Error loading tests in all_tests_view: %s", exc)
        articles = []

    themes = ["All", "Economy", "Society", "Education", "Technology", "Science", "Environment", "Culture", "Health", "General"]
    genres = ["All", "scientific", "narrative", "persuasive", "poetry", "general"]

    paginator = Paginator(articles, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "themes": themes,
        "genres": genres,
        "selected_theme": selected_theme,
        "selected_genre": selected_genre,
        "search_query": query,
    }
    return render(request, "readspace/all_tests.html", context)


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

    user_id = request.user.id if request.user.is_authenticated else 0

    attempt_data = {
        "user_id": user_id,
        "article_id": pk,
        "score": score,
        "total_questions": total_questions,
        "answers": answers,
        "highlighted_markdown": highlighted_markdown,
        "elapsed_time": elapsed_time,
        "submitted_at": datetime.utcnow(),
    }

    model = AttemptMongoModel(**attempt_data)
    model_dict = model.model_dump(by_alias=True, exclude={"id"})

    inserted_id, related = save_attempt(model_dict, pk, highlighted_markdown)
    
    if not inserted_id:
        return JsonResponse({"status": "error", "message": "Failed to save attempt to DB"}, status=500)

    return JsonResponse({"status": "success", "id": inserted_id, "related_articles": related})


@require_POST
@login_required(login_url='/login/')
@csrf_exempt
@api_error_handler
def smart_paraphrase_api(request, pk: str):
    data = json.loads(request.body)
    highlighted_text = data.get("highlighted_text", "").strip()
    paragraph_text = data.get("paragraph_text", "").strip()
    start_idx = data.get("start_index", 0)
    end_idx = data.get("end_index", 0)

    if not highlighted_text or not paragraph_text:
        return JsonResponse({"status": "error", "message": "Missing text data"}, status=400)
        
    paragraph_hash = hashlib.md5(paragraph_text.encode('utf-8')).hexdigest()

    paraphrase_data = get_smart_paraphrase(
        pk, paragraph_hash, highlighted_text, paragraph_text, start_idx, end_idx
    )
    
    if not paraphrase_data:
        return JsonResponse({"status": "error", "message": "Failed to generate paraphrase"}, status=500)

    return JsonResponse({
        "status": "success",
        "expanded_text": paraphrase_data.get("original_expanded_text"),
        "paraphrased_text": paraphrase_data.get("paraphrased_text"),
        "start_index": paraphrase_data.get("start_index"),
        "end_index": paraphrase_data.get("end_index")
    })


@require_POST
@login_required(login_url='/login/')
@csrf_exempt
@api_error_handler
def save_markers_api(request, pk: str):
    data = json.loads(request.body)
    highlighted_markdown = data.get("highlighted_markdown", "")
    
    attempt_data = {
        "user_id": request.user.id,
        "article_id": pk,
        "highlighted_markdown": highlighted_markdown,
        "submitted_at": datetime.utcnow(),
    }

    model = AttemptMongoModel(**attempt_data)
    model_dict = model.model_dump(by_alias=True, exclude={"id"})
    
    inserted_id, _ = save_attempt(model_dict, pk, "")
    
    if inserted_id:
        return JsonResponse({"status": "success", "id": inserted_id})
    return JsonResponse({"status": "error", "message": "Failed to save markers to DB"}, status=500)


@require_GET
@api_error_handler
def search_bm25_api(request):
    query = request.GET.get("q", "").strip()
    if not query:
        return JsonResponse({"status": "error", "message": "Missing query"}, status=400)
        
    results = search_bm25_articles(query)
    return JsonResponse({"status": "success", "results": results})


@require_GET
@api_error_handler
def search_semantic_api(request):
    query = request.GET.get("q", "").strip()
    if not query:
        return JsonResponse({"status": "error", "message": "Missing query"}, status=400)
        
    results = search_semantic_articles(query)
    return JsonResponse({"status": "success", "results": results})


@csrf_exempt
@api_error_handler
def run_ai_tool_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=405)
    try:
        body = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    tool_name = body.get("tool_name")
    version = body.get("version")
    input_data = body.get("input_data", {})

    if not tool_name:
        return JsonResponse({"error": "tool_name is required"}, status=400)

    from service.ai_core.platform import get_ai_tool
    try:
        tool = get_ai_tool(tool_name, version)
    except KeyError as e:
        return JsonResponse({"error": str(e)}, status=404)

    user_id = request.user.id if request.user.is_authenticated else None
    result = tool.run(input_data, user_id=user_id)
    return JsonResponse(result.model_dump(mode="json"))

