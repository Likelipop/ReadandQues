from django.db import models
from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

# ==========================================
# 1. PARAGRAPH CHUNKS (Cập nhật theo Node A & B)
# ==========================================
class ChunkMetadata(BaseModel):
    difficulty: str = Field(default="medium", description="easy, medium, hard")
    main_idea: str = Field(default="")
    keywords: List[str] = Field(default_factory=list)

class ArticleChunk(BaseModel):
    chunk_id: str = Field(..., description="e.g., chunk_1, chunk_2")
    content: str = Field(..., description="Raw paragraph text grouped together")
    source_paragraph_indices: List[int] = Field(..., description="Original paragraph indexes used")
    metadata: ChunkMetadata

# ==========================================
# 2. DETAILED EXAM QUESTIONS (QUIZ ITEM)
# ==========================================
class QuizItem(BaseModel):
    quiz_type: str = Field(..., description="multiple_choice or fill_in_blank")
    question: str = Field(...)
    options: Optional[List[str]] = Field(default=None, description="Only for multiple_choice")
    correct_answer: str = Field(...)
    explanation: str = Field(...)
    
    # IELTS Psychometrics Traceability
    source_chunk_ids: Union[List[str], str] = Field(..., description="IDs of chunks or -1 for whole passage")
    supporting_text: str = Field(..., description="Verbatim sentence from the text")

# ==========================================
# 3. EXAM CLASS & MAIN MONGO SCHEMA (Giữ nguyên cấu trúc nhúng 1:N)
# ==========================================
class Exam(BaseModel):
    exam_id: str = Field(..., description="Unique generated code for this exam")
    title: str = Field(default="IELTS Academic Reading Test")
    total_questions: int = Field(...)
    quizzes: List[QuizItem] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ArticleMongoModel(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id") 
    url: str = Field(...)
    title: str = Field(...)
    original_text: str = Field(...)
    source_name: Optional[str] = Field(default="Unknown")
    
    analysis_review: Optional[str] = Field(default=None, description="Examiner review from Node A")
    chunks: List[ArticleChunk] = Field(default_factory=list)
    exams: List[Exam] = Field(default_factory=list)
    
    error_message: Optional[str] = Field(default=None, description="Optional error message when processing fails")
    status: str = Field(default="pending")
    user_id: Optional[int] = Field(default=None, description="The ID of the Django User who imported this article")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }