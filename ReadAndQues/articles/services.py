import os
from ai_core.graph import app
from .utils.crawler import crawl_article_content

def process_and_analyze_article(url: str) -> dict | None:
    # 1. Gọi hàm cào bài báo (trả về một Dict)
    crawl_result = crawl_article_content(url)
    
    # 2. Kiểm tra trạng thái cào báo thành công
    if not crawl_result.get("success"):
        print(f"❌ Lỗi cào báo: {crawl_result.get('error')}")
        return None

    # Trích xuất dữ liệu sạch từ Dict trả về
    title = crawl_result.get("title", "").strip()
    plain_text = crawl_result.get("content", "").strip()

    if not plain_text:
        return None

    # Ép kiểu tường minh cho Pylance nhận diện đúng GraphState
    text_content = str(plain_text)
    
    # 3. Chuẩn bị session và kích hoạt AI LangGraph
    session_id = f"session_{int(os.times().elapsed * 1000)}"
    config = {"configurable": {"thread_id": session_id}}
    
    print("🧠 Đang gửi nội dung thực tế qua LangGraph...")
    ai_result = app.invoke({"original_text": text_content}, config)

    # 4. Trả về payload chuẩn để lưu vào MongoDB
    return {
        "url": url,
        "title": title or ai_result.get("analysis", {}).get("main_idea", "English Article"),
        "original_text": text_content,
        "source_name": "The Guardian" if "theguardian.com" in url else "Unknown",
        "analysis": ai_result.get("analysis", {}),
        "quizzes": ai_result.get("quizzes", []),
        "status": "completed",
    }