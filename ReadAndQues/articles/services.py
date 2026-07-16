import os
from ai_core.graph import app
from .utils.crawler import crawl_article_content
# from .utils.db import get_article_document_by_id, article_collection

def process_and_analyze_article(url: str) -> dict | None:
    crawl_result = crawl_article_content(url)
    if not crawl_result.get("success"):
        return None

    title = crawl_result.get("title", "").strip()
    plain_text = crawl_result.get("content", "").strip()
    
    # Tách đoạn thô bằng Python để truyền vào GraphState
    raw_paragraphs = [p.strip() for p in plain_text.split("\n\n") if p.strip()]

    session_id = f"session_{int(os.times().elapsed * 1000)}"
    config = {"configurable": {"thread_id": session_id}}
    
    # Nhồi cấu hình Config vào State
    inputs = {
        "original_text": plain_text,
        "paragraphs": raw_paragraphs,
        "exam_config": {
            "total_questions": 14,
            "hard_questions": 7
        }
    }
    
    print("🧠 Running Parallel IELTS Item Generator Graph (5-Node Architecture)...")
    ai_result = app.invoke(inputs, config)

    # Trả về payload map với ArticleMongoModel
    return {
        "url": url,
        "title": title,
        "original_text": plain_text,
        "source_name": "Unknown",
        "analysis_review": ai_result.get("article_analysis", {}).get("examiner_review", ""),
        "chunks": ai_result.get("chunks", []),
        "exams": [ai_result.get("final_exam")], 
        "status": "completed",
    }