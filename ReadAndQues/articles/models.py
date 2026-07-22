from django.db import models

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ==========================================
# 1. QUIZ ITEM — Align với ai_core/schemas.py
# ==========================================
class QuizItem(BaseModel):
    """
    Schema chuẩn cho 1 câu hỏi được lưu vào MongoDB.
    Hỗ trợ 2 loại:
      - yes_no_not_given : câu hỏi Yes/No/Not Given (IELTS Reading)
      - fill_in_blank    : Summary Completion (5 blanks, trả lời phân cách ' | ')
    """
    quiz_type: str = Field(
        ...,
        description="Loại câu hỏi: 'yes_no_not_given' hoặc 'fill_in_blank'"
    )
    question: str = Field(
        ...,
        description=(
            "For yes_no_not_given: the statement to evaluate. "
            "For fill_in_blank: the summary paragraph containing [1]..[5]."
        )
    )
    options: Optional[List[str]] = Field(
        default=None,
        description="For yes_no_not_given: ['Yes', 'No', 'Not Given']. For fill_in_blank: null."
    )
    correct_answer: str = Field(
        ...,
        description=(
            "For yes_no_not_given: 'Yes', 'No', or 'Not Given'. "
            "For fill_in_blank: 5 answers separated by ' | ' (e.g. 'word1 | word2 | word3 | word4 | word5')."
        )
    )
    explanation: Optional[str] = Field(
        default="",
        description="Giải thích chi tiết tại sao đáp án đúng."
    )
    supporting_text: Optional[str] = Field(
        default="",
        description="Verbatim sentence(s) from the article supporting the answer."
    )
    reading_skill: Optional[str] = Field(
        default=None,
        description=(
            "Reading skill tested. One of: 'inference', 'main_idea', "
            "'author_purpose', 'detail', 'vocabulary_in_context'."
        )
    )


# ==========================================
# 2. SCHEMA CHÍNH ĐỂ LƯU VÀO MONGODB
# ==========================================
class ArticleMongoModel(BaseModel):
    """
    Document chính lưu vào MongoDB collection 'articles'.

    Lưu ý thiết kế:
      - `analysis` đã được loại bỏ: phân tích bài là nội bộ của mega prompt,
        không cần lưu vào DB để tiết kiệm storage.
      - `exam_config` được thêm để lưu cấu hình đề thi (số câu, v.v.)
      - `quizzes` chứa toàn bộ câu hỏi (MCQ + FIB) — align với ai_core/schemas.ExamOutput
    """
    # PyMongo trả về _id dưới dạng ObjectId, map sang str
    id: Optional[str] = Field(default=None, alias="_id")

    url: str = Field(..., description="URL gốc của bài báo")
    title: str = Field(..., description="Tiêu đề bài báo")
    original_text: str = Field(..., description="Toàn bộ nội dung thô cào được")
    clean_text: Optional[str] = Field(default=None, description="Text đã dọn sạch (sau Smart Cleaner)")
    source_name: Optional[str] = Field(default="Unknown", description="Tên tờ báo, ví dụ: BBC, CNN")

    # Cấu hình đề thi được dùng khi generate (để audit/re-generate sau này)
    exam_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Cấu hình generate, VD: {\"total_questions\": 10}"
    )

    # Toàn bộ câu hỏi (MCQ Yes/No/NG trước, FIB Summary Completion sau)
    quizzes: List[QuizItem] = Field(default_factory=list)

    # Metadata quản lý trạng thái luồng xử lý
    status: str = Field(
        default="pending",
        description="Trạng thái: pending | processing | completed | failed"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }
