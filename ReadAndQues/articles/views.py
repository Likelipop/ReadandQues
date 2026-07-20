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

    from worker_service.data_pipeline.bronze_one import ingest_one as bronze_ingest

    bronze_result = bronze_ingest(url, user_id=request.user.id)
    if not bronze_result.get("success"):
        # Rollback star since crawl failed
        with transaction.atomic():
            profile = UserProfile.objects.select_for_update().get(user=request.user)
            profile.stars += 1
            profile.save()

        err_msg = bronze_result.get("error", "Không thể trích xuất nội dung từ bài báo này.")
        if _is_ajax(request):
            return JsonResponse({"status": "error", "message": err_msg}, status=400)
        messages.error(request, err_msg)
        return render(request, "articles/import.html", {"stars": request.user.profile.stars})

    # Validate and clean in Silver stage
    from worker_service.data_pipeline.silver import process_one_silver
    
    silver_result = process_one_silver(bronze_result["bronze_id"])
    if not silver_result.get("success"):
        with transaction.atomic():
            profile = UserProfile.objects.select_for_update().get(user=request.user)
            profile.stars += 1
            profile.save()
        err_msg = silver_result.get("error", "Bài báo không đủ điều kiện (quá ngắn hoặc quá dài).")
        if _is_ajax(request):
            return JsonResponse({"status": "error", "message": err_msg}, status=400)
        messages.error(request, err_msg)
        return render(request, "articles/import.html", {"stars": request.user.profile.stars})
        
    silver_doc = silver_result.get("silver_doc", {})

    # Insert into gold_articles with pending status for async AI processing
    pending_document = {
        "silver_id": silver_result["silver_id"],
        "url": url,
        "title": silver_doc.get("title", ""),
        "original_text": silver_doc.get("original_text", ""),
        "source_name": silver_doc.get("source_name", "Unknown"),
        "image_url": silver_doc.get("image_url"),
        "image_urls": silver_doc.get("image_urls") or [],
        "status": "pending",
        "user_id": request.user.id,
        "created_at": datetime.utcnow(),
    }
    inserted_id = insert_article_document(pending_document)

    from worker_service.data_pipeline.gold import process_one_gold_async
    thread = threading.Thread(
        target=process_one_gold_async,
        args=(silver_result["silver_id"], inserted_id),
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
            "image_url":     doc.get("image_url", ""),
            "source_name":   doc.get("source_name", "Unknown"),
        })()

    # Get related articles using ChromaDB
    related_articles = []
    try:
        import sys
        from pathlib import Path
        _PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
        if str(_PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(_PROJECT_ROOT))
        
        from worker_service.ai_core.chroma_client import articles_collection
        
        if articles_collection and hasattr(article, 'analysis') and article.analysis:
            if hasattr(article.analysis, "core"):
                summary = article.analysis.core.summary
            elif isinstance(article.analysis, dict):
                summary = article.analysis.get("core", {}).get("summary", "")
            else:
                summary = ""
                
            if summary:
                # Query top 6 to ensure we get 5 even if the current one is included
                results = articles_collection.query(
                    query_texts=[summary],
                    n_results=6
                )
                
                if results and results['ids']:
                    related_ids = [str(r_id) for r_id in results['ids'][0] if str(r_id) != str(pk)][:5]
                    
                    if related_ids:
                        from bson import ObjectId
                        object_ids = [ObjectId(rid) for rid in related_ids]
                        from .utils.db import article_collection
                        
                        # Fetch the articles from Mongo
                        cursor = article_collection.find({"_id": {"$in": object_ids}})
                        related_docs = {str(d["_id"]): d for d in cursor}
                        
                        # Maintain similarity order
                        for rid in related_ids:
                            if rid in related_docs:
                                r_doc = related_docs[rid]
                                r_doc["id"] = str(r_doc["_id"])
                                related_articles.append(r_doc)
                                
        with open("/tmp/django_debug.txt", "w") as f:
            f.write(f"related_articles len: {len(related_articles)}\n")
            if related_articles:
                f.write(f"First ID: {related_articles[0]['id']}\n")
    except Exception as e:
        import logging
        import traceback
        logging.getLogger(__name__).error(f"Error fetching related articles: {e}")
        with open("/tmp/django_debug.txt", "w") as f:
            f.write(f"Exception: {e}\n{traceback.format_exc()}\n")

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