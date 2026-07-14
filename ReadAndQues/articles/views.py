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


def import_article(request):
    """
    Xử lý tiếp nhận URL, cào báo, validate qua Pydantic Schema và lưu vào MongoDB
    """
    if request.method == "POST":
        url = request.POST.get("url", "").strip()
        
        if not url:
            messages.error(request, "Vui lòng nhập URL bài báo!")
            return render(request, "articles/import.html")
            
        # 2. Kiểm tra trùng lặp URL trong MongoDB
        existing_doc = article_collection.find_one({"url": url})
        if existing_doc:
            messages.info(request, "Bài báo này đã tồn tại trong hệ thống.")
            # Chuyển đổi ObjectId thành chuỗi string để làm tham số URL
            return redirect("articles:article_detail", pk=str(existing_doc["_id"]))
            
        # 3. Tiến hành gọi bộ cào dữ liệu chữ thuần từ utils/
        crawl_result = crawl_article_content(url)
        
        if crawl_result["success"]:
            try:
                # 4. Tạo Object thông qua Pydantic để Validate dữ liệu đầu vào
                # Ở bước Tuần 1 này, ta lưu trạng thái 'pending' và các trường phân tích/quiz tạm để trống (None / rỗng)
                pydantic_article = ArticleMongoModel(
                    url=url,
                    title=crawl_result["title"],
                    original_text=crawl_result["content"],
                    source_name=crawl_result.get("source_name", "Unknown"),
                    status="pending",
                    created_at=datetime.utcnow()
                )
                
                # 5. Đẩy dữ liệu đã được validate vào MongoDB dưới dạng Dictionary (JSON)
                # Dùng mode_dump(by_alias=True) để Pydantic hiểu biến id thành _id của MongoDB
                doc_to_insert = pydantic_article.model_dump(by_alias=True, exclude_none=True)
                
                # Đảm bảo xóa trường _id nếu nó đang là None để MongoDB tự sinh ObjectId
                if "_id" in doc_to_insert and doc_to_insert["_id"] is None:
                    del doc_to_insert["_id"]
                    
                result = article_collection.insert_one(doc_to_insert)
                
                messages.success(request, "Cào dữ liệu và lưu vào MongoDB thành công!")
                return redirect("articles:article_detail", pk=str(result.inserted_id))
                
            except Exception as e:
                messages.error(request, f"Lỗi Validate dữ liệu hoặc lưu DB: {str(e)}")
        else:
            messages.error(request, f"Cào báo thất bại: {crawl_result['error']}")
            
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