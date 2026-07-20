import threading
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import redirect, render
from pydantic import ValidationError

from .models import ArticleMongoModel

from .utils.db import (
    get_article_document_by_id,
    get_articles_by_user,
    insert_article_document,
    update_article_document,
    get_completed_articles,
)


def _is_ajax(request) -> bool:
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


@login_required(login_url="login")
def import_article_view(request):
    if request.method != "POST":
        return render(request, "articles/import.html", {"stars": request.user.profile.stars})

    # 1. Deduct Star
    from .services import deduct_user_star, refund_user_star, import_and_trigger_pipeline
    
    success, err_msg = deduct_user_star(request.user)
    if not success:
        if _is_ajax(request):
            return JsonResponse({"status": "error", "message": err_msg}, status=403 if err_msg == "NO_STARS" else 500)
        messages.error(request, "Bạn đã hết Star! Vui lòng liên hệ để yêu cầu thêm star." if err_msg == "NO_STARS" else err_msg)
        return render(request, "articles/import.html", {"stars": request.user.profile.stars if request.user.profile else 0})

    url = request.POST.get("url", "").strip()
    
    # 2. Trigger Pipeline
    success, err_msg, inserted_id = import_and_trigger_pipeline(url, request.user.id)
    
    if not success:
        refund_user_star(request.user)
        if _is_ajax(request):
            return JsonResponse({"status": "error", "message": err_msg}, status=400)
        messages.error(request, err_msg)
        return render(request, "articles/import.html", {"stars": request.user.profile.stars})

    if _is_ajax(request):
        return JsonResponse({"status": "started", "id": inserted_id})

    return redirect("article_detail", pk=inserted_id)


import_article = import_article_view



@login_required(login_url="login")
def article_status(request, pk):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])

    doc = get_article_document_by_id(pk)
    if not doc:
        return JsonResponse(
            {"status": "error", "message": "Không tìm thấy bài báo."},
            status=404,
        )

    if doc.get("user_id") != request.user.id:
        return JsonResponse(
            {"status": "error", "message": "Bạn không có quyền truy cập bài báo này."},
            status=403,
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


@login_required(login_url="login")
def article_detail(request, pk):
    doc = get_article_document_by_id(pk)
    if not doc:
        messages.error(request, "Không tìm thấy bài báo yêu cầu!")
        return redirect("home")

    # Relax restriction: users can view/practice completed articles created by others (All Tests / Trending)
    # But pending or failed imports are restricted to their owner.
    if doc.get("status") != "completed" and doc.get("user_id") != request.user.id:
        messages.error(request, "Bạn không có quyền xem bài báo này!")
        return redirect("home")

    doc["_id"] = str(doc["_id"])

    try:
        article = ArticleMongoModel.model_validate(doc)
    except ValidationError:
        article = type("PendingArticle", (), {
            "title":         doc.get("title", ""),
            "original_text": doc.get("original_text", ""),
            "exams":         doc.get("exams") or [{"quizzes": []}],
            "status":        doc.get("status", "pending"),
            "id":            str(doc.get("_id")),
            "url":           doc.get("url", ""),
            "analysis":      doc.get("analysis"),
            "image_url":     doc.get("image_url", ""),
            "source_name":   doc.get("source_name", "Unknown"),
        })()

    from .services import get_related_articles_via_chroma
    related_articles = get_related_articles_via_chroma(article, exclude_id=str(pk))

    return render(request, "articles/detail.html", {
        "article": article,
        "related_articles": related_articles
    })


def all_tests_view(request):
    from django.core.paginator import Paginator
    
    selected_theme = request.GET.get("theme", "All")
    selected_genre = request.GET.get("genre", "All")

    articles = get_completed_articles(
        theme=selected_theme if selected_theme != "All" else None,
        genre=selected_genre if selected_genre != "All" else None,
    )

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
    return render(request, "articles/all_tests.html", context)