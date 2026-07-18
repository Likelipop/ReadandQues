import threading
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import redirect, render
from pydantic import ValidationError

from .models import ArticleMongoModel
from .services import process_and_analyze_article
from .utils.db import (
    get_article_document_by_id,
    get_articles_by_user,
    insert_article_document,
    update_article_document,
)


def _run_article_generation(url: str, pk: str) -> None:
    try:
        payload = process_and_analyze_article(url)
        if not payload:
            update_article_document(pk, {
                "status": "failed",
                "error_message": "Không thể trích xuất nội dung từ bài báo này.",
            })
            return
        update_article_document(pk, payload)
    except Exception as e:
        update_article_document(pk, {
            "status": "failed",
            "error_message": str(e),
        })


def _is_ajax(request) -> bool:
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


@login_required(login_url="login")
def import_article_view(request):
    if request.method != "POST":
        return render(request, "articles/import.html")

    url = request.POST.get("url", "").strip()
    if not url:
        if _is_ajax(request):
            return JsonResponse(
                {"status": "error", "message": "Vui lòng nhập một URL bài báo hợp lệ!"},
                status=400,
            )
        messages.error(request, "Vui lòng nhập một URL bài báo hợp lệ!")
        return render(request, "articles/import.html")

    from .utils.crawler import crawl_article_content

    crawl_res = crawl_article_content(url)
    if not crawl_res.get("success"):
        err_msg = crawl_res.get("error", "Không thể trích xuất nội dung từ bài báo này.")
        if _is_ajax(request):
            return JsonResponse({"status": "error", "message": err_msg}, status=400)
        messages.error(request, err_msg)
        return render(request, "articles/import.html")

    pending_document = {
        "url": url,
        "title": crawl_res.get("title", ""),
        "original_text": crawl_res.get("content", ""),
        "status": "pending",
        "user_id": request.user.id,
        "created_at": datetime.utcnow(),
    }
    inserted_id = insert_article_document(pending_document)

    thread = threading.Thread(
        target=_run_article_generation,
        args=(url, inserted_id),
        daemon=True,
    )
    thread.start()

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

    if doc.get("user_id") != request.user.id:
        messages.error(request, "Bạn không có quyền xem bài báo này!")
        return redirect("home")

    doc["_id"] = str(doc["_id"])

    try:
        article = ArticleMongoModel.model_validate(doc)
    except ValidationError:
        article = type("PendingArticle", (), {
            "title": doc.get("title", ""),
            "original_text": doc.get("original_text", ""),
            "exams": doc.get("exams") or [{"quizzes": []}],
            "status": doc.get("status", "pending"),
            "id": str(doc.get("_id")),
            "url": doc.get("url", ""),
        })()

    return render(request, "articles/detail.html", {"article": article})