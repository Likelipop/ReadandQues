import json
import hashlib
import logging
from datetime import datetime, timezone
from bson import ObjectId

from django.contrib import messages
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from django.core.paginator import Paginator

from pipeline.etl.registry import get_pipe
from pipeline.orchestrator import run_article_pipeline_async, run_ai_only_pipeline_async
from database.Mongo.crud import (
    get_article_document_by_url,
    insert_article_document,
    get_article_document_by_id,
    update_article_document,
)
from database.BM25.operations import search_bm25
from database.BM25.text_preprocessing import process_text_to_tokens
from database.Chroma.operations import search_by_text
from database.Mongo.connection import article_collection

from .models import AttemptMongoModel
from .decorators import api_error_handler, rate_limit
from .utils import consume_user_star

logger = logging.getLogger(__name__)

# --- Core Views ---

@require_GET
@login_required(login_url='/login/')
@never_cache
def readspace_view(request, pk):
    """Displays the article in the new 3-column Reading Space layout."""
    doc = get_article_document_by_id(pk)
    if not doc:
        messages.error(request, "Requested article not found!")
        return redirect("home")

    doc["id"] = str(doc.get("_id", pk))
    doc.setdefault("exams", [{"quizzes": []}])

    pipe = get_pipe("related_articles_pipe")
    pipe_result = pipe.invoke(article=doc, exclude_id=str(pk), limit=5)
    related_articles = pipe_result.get("context", {}).get("related_articles", [])
    
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
        existing_doc = get_article_document_by_url(url)
        inserted_id = None
        is_reused = False
        
        if existing_doc and existing_doc.get("status") in ("crawling", "processing", "completed"):
            inserted_id = str(existing_doc.get("_id"))
            is_reused = True
        else:
            pending_document = {
                "url": url,
                "title": "Loading title...",
                "original_text": "",
                "status": "crawling",
                "user_id": user_id,
                "created_at": datetime.now(timezone.utc),
            }
            inserted_id = insert_article_document(pending_document)
            run_article_pipeline_async(inserted_id, url)

    # If reused, refund the star manually or we can let context manager know via an exception, 
    # but since it's a success path, we can refund directly here as a business rule.
    if is_reused and request.user.is_authenticated:
        from .utils import UserProfile
        from django.db import transaction
        try:
            with transaction.atomic():
                profile = UserProfile.objects.select_for_update().get(user=request.user)
                profile.stars += 1
                profile.save()
        except Exception as e:
            logger.error(f"Error refunding star on reuse: {e}")

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"status": "started", "id": inserted_id})

    return redirect("readspace:readspace_detail", pk=inserted_id)

@require_POST
@api_error_handler
def trigger_quiz(request, pk):
    article = get_article_document_by_id(pk)
    if not article:
        return JsonResponse({"status": "error", "message": "Article not found"}, status=404)
        
    update_article_document(pk, {"ai_status": "pending_generation"})
    run_ai_only_pipeline_async(pk)
    
    return JsonResponse({"status": "processing"})

@require_GET
@api_error_handler
def article_status(request, pk):
    doc = get_article_document_by_id(pk)
    if not doc:
        return JsonResponse({"status": "error", "message": "Article not found."}, status=404)

    status = doc.get("ai_status", doc.get("status", "pending"))
    payload = {
        "status": status,
        "message": doc.get("error_message", ""),
        "title": doc.get("title", ""),
    }

    if status == "completed":
        payload["exams"] = doc.get("exams", [])

    return JsonResponse(payload)

@require_GET
def all_tests_view(request):
    selected_theme = request.GET.get("theme", "All")
    selected_genre = request.GET.get("genre", "All")

    completed_result = get_pipe("get_completed_articles_pipe").invoke(
        theme=selected_theme if selected_theme != "All" else None,
        genre=selected_genre if selected_genre != "All" else None,
        limit=100
    )
    articles = completed_result.get("context", {}).get("articles_list", [])

    attempted_ids = set()
    if request.user.is_authenticated:
        attempt_result = get_pipe("get_user_attempted_ids_pipe").invoke(user_id=request.user.id)
        attempted_ids = attempt_result.get("context", {}).get("attempted_ids", set())

    for art in articles:
        art_id = str(art.get("id") or art.get("_id") or "")
        art["has_attempted"] = art_id in attempted_ids

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
    
    save_result = get_pipe("save_exam_attempt_pipe").invoke(
        attempt_data=model.model_dump(by_alias=True, exclude={"id"})
    )
    inserted_id = save_result.get("context", {}).get("inserted_id")
    
    if not inserted_id:
        return JsonResponse({"status": "error", "message": "Failed to save attempt to DB"}, status=500)

    related_result = get_pipe("find_related_by_markers_pipe").invoke(
        highlighted_markdown=highlighted_markdown, 
        article_id=str(pk), 
        limit=5
    )
    related = related_result.get("context", {}).get("related_articles", [])
    
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

    pipe = get_pipe("smart_ink_pipe")
    pipe_result = pipe.invoke(
        article_id=pk,
        paragraph_hash=paragraph_hash,
        highlighted_text=highlighted_text,
        paragraph_text=paragraph_text,
        start_idx=start_idx,
        end_idx=end_idx
    )
    
    paraphrase_data = pipe_result.get("context", {}).get("paraphrase_data", {})
    
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
    
    save_result = get_pipe("save_exam_attempt_pipe").invoke(
        attempt_data=model.model_dump(by_alias=True, exclude={"id"})
    )
    inserted_id = save_result.get("context", {}).get("inserted_id")
    
    if inserted_id:
        return JsonResponse({"status": "success", "id": inserted_id})
    return JsonResponse({"status": "error", "message": "Failed to save markers to DB"}, status=500)

@require_GET
@api_error_handler
def search_bm25_api(request):
    query = request.GET.get("q", "").strip()
    if not query:
        return JsonResponse({"status": "error", "message": "Missing query"}, status=400)
        
    tokens = process_text_to_tokens(query)
    bm25_results = search_bm25(tokens, n=10)
    bm25_ids = [r["id"] for r in bm25_results]
    
    results = []
    for obj_id in bm25_ids:
        try:
            doc = article_collection.find_one({"_id": ObjectId(obj_id)}, {"title": 1, "created_at": 1, "source_name": 1, "original_text": 1})
            if doc:
                snippet = doc.get("original_text", "")[:150] + "..." if doc.get("original_text") else ""
                results.append({
                    "id": str(doc["_id"]),
                    "title": doc.get("title", "No Title"),
                    "source": doc.get("source_name", "Unknown"),
                    "snippet": snippet,
                    "date": doc.get("created_at").strftime("%Y-%m-%d") if doc.get("created_at") else ""
                })
        except Exception:
            continue
    return JsonResponse({"status": "success", "results": results})

@require_GET
@api_error_handler
def search_semantic_api(request):
    query = request.GET.get("q", "").strip()
    if not query:
        return JsonResponse({"status": "error", "message": "Missing query"}, status=400)
        
    hits = search_by_text(query, limit=5)
    
    results = []
    for hit in hits:
        try:
            obj_id = hit["id"]
            doc = article_collection.find_one({"_id": ObjectId(obj_id)}, {"title": 1, "created_at": 1, "source_name": 1, "original_text": 1})
            if doc:
                snippet = doc.get("original_text", "")[:150] + "..." if doc.get("original_text") else ""
                distance = float(hit.get("distance", 0.0))
                similarity = max(0, min(100, int((1.0 - distance / 2.0) * 100)))
                results.append({
                    "id": str(doc["_id"]),
                    "title": doc.get("title", "No Title"),
                    "source": doc.get("source_name", "Unknown"),
                    "snippet": snippet,
                    "date": doc.get("created_at").strftime("%Y-%m-%d") if doc.get("created_at") else "",
                    "similarity": similarity
                })
        except Exception:
            continue
    return JsonResponse({"status": "success", "results": results})
