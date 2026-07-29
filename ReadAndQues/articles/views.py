"""
articles/views.py — Web Controller / Views Layer.

Contains view functions for handling HTTP requests, delegating business logic
to the services layer, and rendering templates or returning JSON responses.
No heavy LLM or long-running threading logic is performed directly inside views.
"""

from database.Mongo.crud import get_article_document_by_id
from django.contrib import messages
from django.http import HttpResponseNotAllowed, JsonResponse, HttpResponse
from django.shortcuts import redirect, render
from pydantic import ValidationError

from .models import ArticleMongoModel
from .services import import_and_trigger_pipeline


from django.core.cache import cache
from django.contrib.auth.decorators import login_required
@login_required(login_url='/login/')
def import_article_view(request):
    """
    On POST:
      - Validates input URL.
      - Checks rate limit.
      - Calls import_and_trigger_pipeline.
    """
    if request.method == "POST":
        # Rate Limiting
        client_ip = request.META.get('REMOTE_ADDR', 'unknown_ip')
        user_identifier = f"user_{request.user.id}" if request.user.is_authenticated else f"ip_{client_ip}"
        cache_key = f"rate_limit_import_{user_identifier}"
        
        # Limit to 5 requests per 60 seconds
        requests_count = cache.get(cache_key, 0)
        if requests_count >= 5:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"status": "error", "message": "Too many requests. Please wait a minute."}, status=429)
            messages.error(request, "Too many requests. Please wait a minute.")
            return redirect("home")
            
        cache.set(cache_key, requests_count + 1, timeout=60)


        url = request.POST.get("url", "").strip()
        user_id = request.user.id if request.user.is_authenticated else 0

        # Check and deduct star for authenticated users
        if request.user.is_authenticated:
            from .services.user_stars import deduct_user_star, refund_user_star
            success_deduct, err_msg = deduct_user_star(request.user)
            if not success_deduct:
                error_response = "You do not have enough stars to import articles. Please contact support to get more stars."
                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return JsonResponse({"status": "error", "message": error_response}, status=400)
                messages.error(request, error_response)
                return redirect("home")
        else:
            from .services.user_stars import refund_user_star

        is_success, error_msg, inserted_id, is_reused = import_and_trigger_pipeline(url, user_id)

        if not is_success:
            if request.user.is_authenticated:
                refund_user_star(request.user)
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse(
                    {"status": "error", "message": error_msg}, status=400
                )

            messages.error(request, error_msg)
            return redirect("home")

        # If article already exists and is reused, refund the pre-deducted star
        if is_reused and request.user.is_authenticated:
            refund_user_star(request.user)

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"status": "started", "id": inserted_id})

        return redirect("articles:article_detail", pk=inserted_id)

    return redirect("home")


import_article = import_article_view


def article_status(request, pk):
    """API endpoint to poll the background processing status of an article."""
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])

    doc = get_article_document_by_id(pk)
    if not doc:
        return JsonResponse(
            {"status": "error", "message": "Article not found."}, status=404
        )

    status = doc.get("status", "pending")
    payload = {
        "status": status,
        "message": doc.get("error_message", ""),
        "title": doc.get("title", ""),
    }

    if status == "completed":
        payload["exams"] = doc.get("exams", [])

    return JsonResponse(payload)


from django.views.decorators.cache import never_cache

@login_required(login_url='/login/')
@never_cache
def article_detail(request, pk):
    """Displays the article detail page (reading view & generated exams)."""
    doc = get_article_document_by_id(pk)
    if not doc:
        messages.error(request, "Requested article not found!")
        return redirect("articles:import_article")

    doc["_id"] = str(doc["_id"])

    try:
        article = ArticleMongoModel.model_validate(doc)
    except ValidationError:
        title = doc.get("title", "")
        original_text = doc.get("original_text", "")
        status = doc.get("status", "pending")
        url = doc.get("url", "")
        article = type("SimpleArticle", (), {})()
        article.title = title
        article.original_text = original_text
        article.exams = doc.get("exams") or [{"quizzes": []}]
        article.status = status
        article.id = str(doc.get("_id"))
        article.url = url

    from pipeline.etl.registry import get_pipe
    from pipeline.etl import pipes  # Trigger registration
    from database.Mongo.crud import get_completed_articles

    pipe = get_pipe("related_articles_pipe")
    pipe_result = pipe.invoke(article=article, exclude_id=str(pk), limit=5)
    related_articles = pipe_result.get("context", {}).get("related_articles", [])
    
    if not related_articles:
        all_completed = get_completed_articles(limit=10)
        related_articles = [
            a
            for a in all_completed
            if str(a.get("id")) != str(pk) and str(a.get("_id")) != str(pk)
        ][:5]

    return render(
        request,
        "articles/detail.html",
        {"article": article, "related_articles": related_articles},
    )


def all_tests_view(request):
    from database.Mongo.crud import (get_completed_articles,
                                     get_user_attempted_article_ids)
    from django.core.paginator import Paginator

    selected_theme = request.GET.get("theme", "All")
    selected_genre = request.GET.get("genre", "All")

    articles = get_completed_articles(
        theme=selected_theme if selected_theme != "All" else None,
        genre=selected_genre if selected_genre != "All" else None,
    )

    attempted_ids = set()
    if request.user.is_authenticated:
        attempted_ids = get_user_attempted_article_ids(request.user.id)

    for art in articles:
        art_id = str(art.get("id") or art.get("_id") or "")
        art["has_attempted"] = art_id in attempted_ids

    themes = [
        "All",
        "Economy",
        "Society",
        "Education",
        "Technology",
        "Science",
        "Environment",
        "Culture",
        "Health",
        "General",
    ]
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
    return render(request, "articles/all_tests.html", context)


from datetime import datetime

from django.views.decorators.csrf import csrf_exempt


@login_required(login_url='/login/')
@csrf_exempt
def submit_exam_attempt(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    try:
        import json

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

        # validate with pydantic
        from .models import AttemptMongoModel

        model = AttemptMongoModel(**attempt_data)

        from database.Mongo.crud import save_exam_attempt

        inserted_id = save_exam_attempt(model.model_dump(by_alias=True, exclude={"id"}))
        if inserted_id:
            from .services.marker_search import \
                get_related_articles_from_markers

            related = get_related_articles_from_markers(
                highlighted_markdown=highlighted_markdown,
                article_id=str(pk),
                limit=5,
            )
            return JsonResponse(
                {"status": "success", "id": inserted_id, "related_articles": related}
            )
        else:
            return JsonResponse(
                {"status": "error", "message": "Failed to save attempt to DB"},
                status=500,
            )

    except Exception as e:
        import traceback

        traceback.print_exc()
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.cache import never_cache

@login_required(login_url='/login/')
@xframe_options_sameorigin
@never_cache
def raw_html_view(request, pk: str):
    """
    Returns the raw HTML of the article to be rendered inside an iframe.
    If no html_content is present, returns a basic HTML document with the original text.
    """
    from database.Mongo.crud import get_article_document_by_id

    article_data = get_article_document_by_id(pk)
    if not article_data:
        return HttpResponse("Article not found", status=404)

    html_content = article_data.get("html_content")
    if html_content:
        injected_css = "<style>a { cursor: text !important; color: inherit !important; text-decoration: none !important; }</style>"
        injected_js = "<script>document.addEventListener('DOMContentLoaded', function() { document.querySelectorAll('a').forEach(a => { a.removeAttribute('href'); }); });</script>"
        injection = injected_css + injected_js
        if "</head>" in html_content.lower():
            import re
            html_content = re.sub(r'(?i)</head>', f'{injection}</head>', html_content)
        else:
            html_content = injection + html_content
    else:
        # Fallback for old articles without html_content
        text = article_data.get("original_text", "")
        html_content = f"<html><body style='font-family:sans-serif; padding: 20px;'><pre style='white-space: pre-wrap; font-family: inherit;'>{text}</pre></body></html>"

    return HttpResponse(html_content, content_type="text/html; charset=utf-8")


@login_required(login_url='/login/')
@csrf_exempt
def smart_paraphrase_view(request, pk: str):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    try:
        import json
        import hashlib
        
        data = json.loads(request.body)
        highlighted_text = data.get("highlighted_text", "").strip()
        paragraph_text = data.get("paragraph_text", "").strip()
        start_idx = data.get("start_index", 0)
        end_idx = data.get("end_index", 0)

        if not highlighted_text or not paragraph_text:
            return JsonResponse({"status": "error", "message": "Missing text data"}, status=400)
            
        # Hash the paragraph for quicker DB matching
        paragraph_hash = hashlib.md5(paragraph_text.encode('utf-8')).hexdigest()

        from pipeline.etl.registry import get_pipe
        from pipeline.etl import pipes  # Trigger registration
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

        # We return the exact indices and texts so the frontend can animate properly
        return JsonResponse({
            "status": "success",
            "expanded_text": paraphrase_data.get("original_expanded_text"),
            "paraphrased_text": paraphrase_data.get("paraphrased_text"),
            "start_index": paraphrase_data.get("start_index"),
            "end_index": paraphrase_data.get("end_index")
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": str(e)}, status=400)

