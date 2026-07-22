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


def import_article_view(request):
    """
    On POST:
      - Validates input URL.
      - Calls import_and_trigger_pipeline service to ingest article and queue AI exam generation via Celery.
      - Redirects user immediately to the reading/detail view (or returns JSON for AJAX clients).
    On GET:
      - Redirects to home since there is no separate import page anymore.
    """
    if request.method == "POST":
        url = request.POST.get("url", "").strip()
        user_id = request.user.id if request.user.is_authenticated else 0

        is_success, error_msg, inserted_id = import_and_trigger_pipeline(url, user_id)

        if not is_success:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse(
                    {"status": "error", "message": error_msg}, status=400
                )

            messages.error(request, error_msg)
            return redirect("home")

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
            {"status": "error", "message": "Không tìm thấy bài báo."}, status=404
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


def article_detail(request, pk):
    """Displays the article detail page (reading view & generated exams)."""
    doc = get_article_document_by_id(pk)
    if not doc:
        messages.error(request, "Không tìm thấy bài báo yêu cầu!")
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

    from database.Chroma.operations import get_related_articles_via_chroma
    from database.Mongo.crud import get_completed_articles

    related_articles = get_related_articles_via_chroma(article, exclude_id=str(pk))
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
    from database.Mongo.crud import get_completed_articles
    from django.core.paginator import Paginator

    selected_theme = request.GET.get("theme", "All")
    selected_genre = request.GET.get("genre", "All")

    articles = get_completed_articles(
        theme=selected_theme if selected_theme != "All" else None,
        genre=selected_genre if selected_genre != "All" else None,
    )

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


def raw_html_view(request, pk: str):
    """
    Returns the raw HTML of the article to be rendered inside an iframe.
    If no html_content is present, returns a basic HTML document with the original text.
    """
    from database.Mongo.crud import get_article_document

    article_data = get_article_document(pk)
    if not article_data:
        return HttpResponse("Article not found", status=404)

    html_content = article_data.get("html_content")
    if not html_content:
        # Fallback for old articles without html_content
        text = article_data.get("original_text", "")
        html_content = f"<html><body style='font-family:sans-serif; padding: 20px;'><pre style='white-space: pre-wrap; font-family: inherit;'>{text}</pre></body></html>"

    return HttpResponse(html_content, content_type="text/html; charset=utf-8")
