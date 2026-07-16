from django.shortcuts import render, redirect
from django.contrib import messages
from .models import ArticleMongoModel
from .services import process_and_analyze_article
from .utils.db import insert_article_document, get_article_document_by_id

def import_article(request):
    if request.method == "POST":
        url = request.POST.get("url", "").strip()
        if not url:
            messages.error(request, "Vui lòng nhập một URL bài báo hợp lệ!")
            return render(request, "articles/import.html")

        try:
            payload = process_and_analyze_article(url)
            if not payload:
                messages.error(request, "Không thể trích xuất nội dung từ bài báo này.")
                return render(request, "articles/import.html")

            inserted_id = insert_article_document(payload)
            messages.success(request, "Chúc mừng! AI đã phân tích bài viết và tạo bộ câu hỏi thành công.")
            return redirect("articles:article_detail", pk=inserted_id)

        except Exception as e:
            messages.error(request, f"Đã xảy ra lỗi trong quá trình xử lý: {str(e)}")
            return render(request, "articles/import.html")

    return render(request, "articles/import.html")

def article_detail(request, pk):
    doc = get_article_document_by_id(pk)
    if not doc:
        messages.error(request, "Không tìm thấy bài báo yêu cầu!")
        return redirect("articles:import_article")

    doc["_id"] = str(doc["_id"])
    article = ArticleMongoModel.model_validate(doc)
    return render(request, "articles/detail.html", {"article": article})