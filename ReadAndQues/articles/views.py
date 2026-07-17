import threading
from datetime import datetime

from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse, HttpResponseNotAllowed

from .models import ArticleMongoModel
from .services import process_and_analyze_article
from .utils.db import insert_article_document, get_article_document_by_id, update_article_document


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


def import_article_view(request):
    """
    On POST: do a quick crawl synchronously to get title + original_text so user can read immediately.
    Insert a pending document (status="pending") containing url, title, original_text.
    Start full async LangGraph processing in background which will update the document to include chunks/exams and status="completed".

    Behavior:
    - If request is AJAX (X-Requested-With), return JSON (useful for API clients)
    - Otherwise redirect to the article_detail page immediately so user can start reading.
    """
    if request.method == "POST":
        url = request.POST.get("url", "").strip()
        if not url:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"status": "error", "message": "Vui lòng nhập một URL bài báo hợp lệ!"}, status=400)

            messages.error(request, "Vui lòng nhập một URL bài báo hợp lệ!")
            return render(request, "articles/import.html")

        # Quick synchronous crawl to give user immediate reading content
        from .utils.crawler import crawl_article_content
        crawl_res = crawl_article_content(url)

        if not crawl_res.get("success"):
            err_msg = crawl_res.get("error", "Không thể trích xuất nội dung từ bài báo này.")
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"status": "error", "message": err_msg}, status=400)
            messages.error(request, err_msg)
            return render(request, "articles/import.html")

        title = crawl_res.get("title", "")
        original_text = crawl_res.get("content", "")

        pending_document = {
            "url": url,
            "title": title,
            "original_text": original_text,
            "status": "pending",
            "created_at": datetime.utcnow(),
        }

        inserted_id = insert_article_document(pending_document)

        # Start longer-running full processing in background (LangGraph etc.)
        thread = threading.Thread(target=_run_article_generation, args=(url, inserted_id), daemon=True)
        thread.start()

        # If AJAX, return immediate JSON with id; otherwise redirect straight to reading view
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"status": "started", "id": inserted_id})

        # Redirect user immediately to the reading view so they can start reading while AI works
        return redirect("article_detail", pk=inserted_id)

    return render(request, "articles/import.html")


import_article = import_article_view


def article_status(request, pk):
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
        # return exams (may be large) so clients can load without a full page refresh if desired
        payload["exams"] = doc.get("exams", [])

    return JsonResponse(payload)


from pydantic import ValidationError


def article_detail(request, pk):
    doc = get_article_document_by_id(pk)
    if not doc:
        messages.error(request, "Không tìm thấy bài báo yêu cầu!")
        return redirect("articles:import_article")

    # expose _id as string for templates
    doc["_id"] = str(doc["_id"])

    try:
        article = ArticleMongoModel.model_validate(doc)
    except ValidationError:
        # Document is incomplete (processing in progress) — create a minimal object usable by templates
        title = doc.get("title", "")
        original_text = doc.get("original_text", "")
        status = doc.get("status", "pending")
        url = doc.get("url", "")
        article = type("SimpleArticle", (), {})()
        # Ensure template keys exist with safe defaults
        article.title = title
        article.original_text = original_text
        article.exams = doc.get("exams") or [{"quizzes": []}]
        article.status = status
        article.id = str(doc.get("_id"))
        article.url = url

    # If the processing hasn't completed yet, show the loading area in the right pane (template will show reading on left)
    if getattr(article, "status", "pending") != "completed":
        # Render same reading/detail template but it will show content on left and either loading placeholder or nothing on right.
        # Using the same detail template simplifies UX: users read immediately; JS in page can poll for status/questions.
        return render(request, "articles/detail.html", {"article": article})

    return render(request, "articles/detail.html", {"article": article})