from django.db import models
from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

# ==========================================
# 1. PARAGRAPH CHUNKS (INDEX MAP)
# ==========================================
class ChunkMetadata(BaseModel):
    difficulty: str = Field("medium", description="easy, medium, hard")
    contains_vocabulary: bool = False
    contains_numbers: bool = False
    contains_grammar: bool = False

class ArticleChunk(BaseModel):
    chunk_id: str = Field(..., description="e.g., chunk_1, chunk_2")
    content: str = Field(..., description="Raw paragraph text")
    paragraph_number: int = Field(...)
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
    source_chunk_id: str = Field(...)
    supporting_text: str = Field(..., description="Verbatim sentence from the text")
    start_char_offset: int = Field(...)
    end_char_offset: int = Field(...)

# ==========================================
# 3. EXAM CLASS (Embedded 1 : N Relationship)
# ==========================================
class Exam(BaseModel):
    exam_id: str = Field(..., description="Unique generated code for this exam")
    title: str = Field(default="IELTS Academic Reading Test")
    total_questions: int = Field(14)
    quizzes: List[QuizItem] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

# ==========================================
# 4. MAIN MONGO SCHEMA
# ==========================================
class ArticleMongoModel(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id") 
    url: str = Field(...)
    title: str = Field(...)
    original_text: str = Field(...)
    source_name: Optional[str] = Field(default="Unknown")
    
    # Embedded components
    chunks: List[ArticleChunk] = Field(default_factory=list)
    exams: List[Exam] = Field(default_factory=list) # 1 Article : N Exams
    
    status: str = Field(default="pending")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }