from django.db import models

from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime

# ==========================================
# 1. PHẦN QUIZ (Hỗ trợ đa dạng các loại câu hỏi)
# ==========================================
class QuizItem(BaseModel):
    quiz_type: str = Field(..., description="Loại câu hỏi: multiple_choice, fill_in_blank, matching, v.v.")
    question: str = Field(..., description="Nội dung câu hỏi")
    
    # Optional vì câu hỏi điền từ hoặc nối từ có thể không cần options như trắc nghiệm
    options: Optional[List[str]] = Field(default=None, description="Danh sách đáp án lựa chọn cho trắc nghiệm")
    
    # Any/Union vì đáp án đúng có thể là chuỗi (A, B, C) hoặc Dict cho bài nối từ
    correct_answer: Any = Field(..., description="Đáp án đúng")
    explanation: Optional[str] = Field(default="", description="Giải thích chi tiết tại sao đáp án này đúng")

# ==========================================
# 2. PHẦN PHÂN TÍCH CHI TIẾT BÀI BÁO (AI Generated)
# ==========================================
class VocabularyItem(BaseModel):
    word: str
    part_of_speech: Optional[str] = None # Từ loại: Noun, Verb, Adj...
    context_meaning: str                    # Nghĩa trong ngữ cảnh bài báo
    example_sentence: Optional[str] = None # Câu ví dụ thực tế trong bài hoặc AI tự tạo

class GrammarItem(BaseModel):
    structure: str                     # Cấu trúc câu ngữ pháp (ví dụ: Cấu trúc đảo ngữ)
    explanation: str                   # Giải thích ngữ pháp
    example: str                       # Câu ví dụ đi kèm

class ArticleAnalysis(BaseModel):
    main_idea: Optional[str] = None                 # Ý chính của toàn bộ bài báo
    paragraph_summaries: List[str] = Field(default_factory=list) # Tóm tắt ý chính của từng đoạn văn
    key_events: List[str] = Field(default_factory=list)          # Các sự kiện/mốc thời gian chính trong bài
    keywords: List[str] = Field(default_factory=list)            # Các từ khóa cốt lõi (Keywords)
    vocabularies: List[VocabularyItem] = Field(default_factory=list) # Danh sách từ vựng chi tiết
    grammar_points: List[GrammarItem] = Field(default_factory=list)  # Các điểm ngữ pháp đáng chú ý

# ==========================================
# 3. SCHEMA CHÍNH ĐỂ LƯU VÀO MONGODB
# ==========================================
class ArticleMongoModel(BaseModel):
    # PyMongo trả về _id dưới dạng ObjectId, ta tạm để str hoặc dùng Field để map nếu cần
    id: Optional[str] = Field(default=None, alias="_id") 
    
    url: str = Field(..., description="URL gốc của bài báo")
    title: str = Field(..., description="Tiêu đề bài báo")
    original_text: str = Field(..., description="Toàn bộ nội dung chữ thô cào được")
    source_name: Optional[str] = Field(default="Unknown", description="Tên tờ báo, ví dụ: BBC, CNN")
    
    # Nhúng (Embed) phần Phân tích và Quizzes vào Document chính
    analysis: Optional[ArticleAnalysis] = None
    quizzes: List[QuizItem] = Field(default_factory=list)
    
    # Metadata quản lý trạng thái luồng xử lý
    status: str = Field(default="pending", description="Trạng thái: pending, processing, completed, failed")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Cấu hình Pydantic để làm việc mượt mà với ObjectId của MongoDB nếu cần
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }
