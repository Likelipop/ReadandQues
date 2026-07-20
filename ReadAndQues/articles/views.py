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
    get_completed_articles,
)


def _run_article_generation(url: str, original_text: str, pk: str) -> None:
    try:
        payload = process_and_analyze_article(url, original_text)
        if not payload:
            update_article_document(pk, {
                "status": "failed",
                "error_message": "AI pipeline không thể xử lý bài báo này.",
            })
            return
        update_article_document(pk, payload)
    except Exception as e:
        update_article_document(pk, {
            "status": "failed",
            "error_message": str(e),
        })


from django.db import transaction
from accounts.models import UserProfile


def _is_ajax(request) -> bool:
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


@login_required(login_url="login")
def import_article_view(request):
    if request.method != "POST":
        return render(request, "articles/import.html", {"stars": request.user.profile.stars})

    # Cyber Security: Check & decrement star count atomically to prevent race condition attacks
    try:
        with transaction.atomic():
            profile = UserProfile.objects.select_for_update().get(user=request.user)
            if profile.stars <= 0:
                if _is_ajax(request):
                    return JsonResponse({"status": "error", "message": "NO_STARS"}, status=403)
                messages.error(request, "Bạn đã hết Star! Vui lòng liên hệ để yêu cầu thêm star.")
                return render(request, "articles/import.html", {"stars": 0})
            
            # Deduct star
            profile.stars -= 1
            profile.save()
    except Exception as e:
        if _is_ajax(request):
            return JsonResponse({"status": "error", "message": "Lỗi hệ thống khi cập nhật số lượng Star."}, status=500)
        messages.error(request, "Lỗi hệ thống khi cập nhật số lượng Star.")
        return render(request, "articles/import.html", {"stars": request.user.profile.stars})

    url = request.POST.get("url", "").strip()
    if not url:
        # Rollback star since the import didn't go through due to invalid input
        with transaction.atomic():
            profile = UserProfile.objects.select_for_update().get(user=request.user)
            profile.stars += 1
            profile.save()

        if _is_ajax(request):
            return JsonResponse(
                {"status": "error", "message": "Vui lòng nhập một URL bài báo hợp lệ!"},
                status=400,
            )
        messages.error(request, "Vui lòng nhập một URL bài báo hợp lệ!")
        return render(request, "articles/import.html", {"stars": request.user.profile.stars})

    from .utils.crawler import crawl_article_content

    crawl_res = crawl_article_content(url)
    if not crawl_res.get("success"):
        # Rollback star since crawl failed
        with transaction.atomic():
            profile = UserProfile.objects.select_for_update().get(user=request.user)
            profile.stars += 1
            profile.save()

        err_msg = crawl_res.get("error", "Không thể trích xuất nội dung từ bài báo này.")
        if _is_ajax(request):
            return JsonResponse({"status": "error", "message": err_msg}, status=400)
        messages.error(request, err_msg)
        return render(request, "articles/import.html", {"stars": request.user.profile.stars})

    pending_document = {
        "url": url,
        "title": crawl_res.get("title", ""),
        "original_text": crawl_res.get("content", ""),
        "source_name": crawl_res.get("source_name", "Unknown"),
        "status": "pending",
        "user_id": request.user.id,
        "created_at": datetime.utcnow(),
    }
    inserted_id = insert_article_document(pending_document)

    thread = threading.Thread(
        target=_run_article_generation,
        args=(url, crawl_res.get("content", ""), inserted_id),
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
            "analysis":      doc.get("analysis"),   # may be None for older docs
        })()

    return render(request, "articles/detail.html", {"article": article})


def all_tests_view(request):
    selected_theme = request.GET.get("theme", "All")
    selected_genre = request.GET.get("genre", "All")

    articles = get_completed_articles(
        theme=selected_theme if selected_theme != "All" else None,
        genre=selected_genre if selected_genre != "All" else None,
    )

    themes = ["All", "Economy", "Society", "Education", "Technology", "Science", "Environment", "Culture", "Health", "General"]
    genres = ["All", "scientific", "narrative", "persuasive", "poetry", "general"]

    context = {
        "articles": articles,
        "themes": themes,
        "genres": genres,
        "selected_theme": selected_theme,
        "selected_genre": selected_genre,
    }
    return render(request, "articles/all_tests.html", context)