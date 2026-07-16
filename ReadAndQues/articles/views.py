from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from datetime import datetime
import pymongo
from bson import ObjectId

from .utils.crawler import crawl_article_content
# Import schema Pydantic bạn vừa định nghĩa
from .models import ArticleMongoModel 

# 1. Khởi tạo kết nối MongoDB (Bạn có thể đưa cụm này vào settings.py hoặc file db_connection riêng)
# Giả sử cấu hình MONGO_URI trong settings, nếu chưa có hãy đổi thành chuỗi cụ thể ví dụ: "mongodb://localhost:27017/"
MONGO_URI = getattr(settings, "MONGO_URI", "mongodb://localhost:27017/")
client = pymongo.MongoClient(MONGO_URI)
db = client[getattr(settings, "MONGO_DB_NAME", "read_and_ques_db")]
article_collection = db["articles"]  # Tên collection trong MongoDB


import os
from django.shortcuts import render, redirect
from django.contrib import messages
from .utils.crawler import crawl_article_content  # Hàm cào báo từ Tuần 1
from ai_core.graph import app  # Đồ thị LangGraph của chúng ta
from .models import ArticleMongoModel  # Pydantic/Mongo Model của bạn

def import_article(request):
    """
    View xử lý dán link bài báo, cào text, chạy qua LangGraph và lưu MongoDB
    """
    if request.method == "POST":
        url = request.POST.get("url", "").strip()
        
        if not url:
            messages.error(request, "Vui lòng nhập một URL bài báo hợp lệ!")
            return render(request, "articles/import.html")
        
        try:
            # 1. Cào nội dung bài báo từ URL
            print(f"🕵️ Đang cào dữ liệu từ URL: {url}...")
            title, plain_text, *_ = crawl_article_content(url)
            
            if not plain_text:
                messages.error(request, "Không thể trích xuất nội dung từ bài báo này. Hãy thử link khác!")
                return render(request, "articles/import.html")
                
            # 2. Chuẩn bị dữ liệu và session đẩy vào LangGraph
            inputs = {"original_text": plain_text}
            # Tạo unique session id từ timestamp để LangGraph theo dõi trạng thái
            session_id = f"session_{int(os.times().elapsed * 1000)}" 
            config = {"configurable": {"thread_id": session_id}}
            
            # 3. Gọi mô hình GPT qua LangGraph
            print("🧠 Đang gửi nội dung qua LangGraph và Azure AI Foundry...")
            ai_result = app.invoke(inputs, config)
            
            # Lấy data đã được phân tách từ các Node trong đồ thị
            analysis_data = ai_result.get("analysis", {})
            quizzes_data = ai_result.get("quizzes", [])
            
            # 4. Khởi tạo Object đúng theo Schema MongoDB của bạn
            print("💾 Lưu thông tin bài báo và bộ quiz vào MongoDB...")
            
            # Tùy thuộc vào cách bạn kết nối PyMongo hay Djongo ở Tuần 1, 
            # Dưới đây là cách tạo document chuẩn bằng việc đưa Dict vào PyMongo hoặc .objects.create()
            # Ví dụ minh họa theo PyMongo / Djongo kết hợp Pydantic:
            article_doc = {
                "url": url,
                "title": title or analysis_data.get("main_idea", "English Article"),
                "original_text": plain_text,
                "source_name": "Unknown",
                "analysis": analysis_data,
                "quizzes": quizzes_data,
                "status": "completed",
            }
            
            # Đoạn này bạn gọi hàm insert vào MongoDB của bạn từ Tuần 1:
            # Giả sử dùng PyMongo: db.articles.insert_one(article_doc)
            # Hoặc nếu dùng Djongo/ORM: inserted_obj = ArticleMongoModel.objects.create(**article_doc)
            
            # Lấy ra ID của bản ghi vừa tạo (ví dụ chuỗi string của ObjectId)
            # inserted_id = str(inserted_obj.id) hoặc str(result.inserted_id)
            inserted_id = "điền_id_sau_khi_insert_thành_công_vào_đây"
            
            messages.success(request, "Chúc mừng! AI đã phân tích bài viết và tạo bộ câu hỏi thành công.")
            
            # 5. Khớp chính xác với đường dẫn: path("<str:pk>/", views.article_detail, name="article_detail")
            return redirect("articles:article_detail", pk=inserted_id)
            
        except Exception as e:
            print(f"❌ Lỗi hệ thống: {str(e)}")
            messages.error(request, f"Đã xảy ra lỗi trong quá trình xử lý: {str(e)}")
            return render(request, "articles/import.html")
            
    return render(request, "articles/import.html")


def article_detail(request, pk):
    """
    Hiển thị chi tiết bài báo lấy từ MongoDB dựa vào ObjectId (pk)
    """
    try:
        # Tìm kiếm bằng ObjectId của MongoDB
        doc = article_collection.find_one({"_id": ObjectId(pk)})
    except Exception:
        doc = None
        
    if not doc:
        messages.error(request, "Không tìm thấy bài báo yêu cầu!")
        return redirect("articles:import_article")
        
    # Map ngược tài liệu từ MongoDB sang Pydantic để dễ dàng gọi thuộc tính trong Template
    # Chuyển đổi _id từ ObjectId thành string để Pydantic không bị lỗi type
    doc["_id"] = str(doc["_id"])
    article = ArticleMongoModel.model_validate(doc)
    
    return render(request, "articles/detail.html", {"article": article})


