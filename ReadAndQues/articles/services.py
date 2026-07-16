import os
from ai_core.graph import app
from .utils.crawler import crawl_article_content
from .utils.db import get_article_document_by_id, article_collection

def process_and_analyze_article(url: str) -> dict | None:
    # 1. Gọi bộ cào bài báo từ Tuần 1
    crawl_result = crawl_article_content(url)
    if not crawl_result.get("success"):
        return None

    title = crawl_result.get("title", "").strip()
    plain_text = crawl_result.get("content", "").strip()

    # 2. Gọi bộ não AI LangGraph song song mới
    session_id = f"session_{int(os.times().elapsed * 1000)}"
    config = {"configurable": {"thread_id": session_id}}
    
    # Cấu hình ma trận IELTS chuẩn: 14 câu hỏi, trong đó có 7 câu khó
    inputs = {
        "original_text": plain_text,
        "total_target_questions": 14,
        "hard_target_count": 7
    }
    
    print("🧠 Running parallel IELTS Item Generator Graph...")
    ai_result = app.invoke(inputs, config)

    # 3. Trả về payload mới khớp 100% với MongoDB Schema mới
    return {
        "url": url,
        "title": title,
        "original_text": plain_text,
        "source_name": "The Guardian" if "theguardian.com" in url else "Unknown",
        "chunks": ai_result.get("chunks", []),
        "exams": [ai_result.get("final_exam")],  # Embedded list of Exams
        "status": "completed",
    }