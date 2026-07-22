"""
articles/views.py — Web Controller / Views Layer.

Contains view functions for handling HTTP requests, delegating business logic
to the services layer, and rendering templates or returning JSON responses.
No heavy LLM or long-running threading logic is performed directly inside views.
"""

from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse, HttpResponseNotAllowed
from pydantic import ValidationError

from .models import ArticleMongoModel
from .services import import_and_trigger_pipeline
from database.Mongo.crud import get_article_document_by_id


def import_article_view(request):
    """
    On POST:
      - Validates input URL.
      - Calls import_and_trigger_pipeline service to ingest article and queue AI exam generation via Celery.
      - Redirects user immediately to the reading/detail view (or returns JSON for AJAX clients).
    On GET:
      - Renders import form template.
    """
    if request.method == "POST":
        url = request.POST.get("url", "").strip()
        user_id = request.user.id if request.user.is_authenticated else 0

        is_success, error_msg, inserted_id = import_and_trigger_pipeline(url, user_id)

        if not is_success:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"status": "error", "message": error_msg}, status=400)
            messages.error(request, error_msg)
            return render(request, "articles/import.html")

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"status": "started", "id": inserted_id})

        return redirect("articles:article_detail", pk=inserted_id)

    return render(request, "articles/import.html")


import_article = import_article_view


def article_status(request, pk):
    """API endpoint to poll the background processing status of an article."""
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])

    doc = get_article_document_by_id(pk)
    if not doc:
        return JsonResponse({"status": "error", "message": "Không tìm thấy bài báo."}, status=404)

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

    return render(request, "articles/detail.html", {"article": article})