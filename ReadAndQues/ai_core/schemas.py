from typing import List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

# ==========================================
# 1. PARAGRAPH CHUNKS (Tối giản theo Master Planner)
# ==========================================
class ChunkMetadata(BaseModel):
    # Đã bỏ keywords và difficulty đi để giảm Output Token của LLM
    main_idea: str = Field(default="", description="Short 5-word summary of the chunk")

class ArticleChunk(BaseModel):
    chunk_id: str = Field(..., description="e.g., chunk_1, chunk_2")
    content: str = Field(..., description="Raw paragraph text grouped together")
    source_paragraph_indices: List[int] = Field(..., description="Original paragraph indexes used")
    metadata: ChunkMetadata

# ==========================================
# 2. DETAILED EXAM QUESTIONS (QUIZ ITEM)
# ==========================================
class QuizItem(BaseModel):
    quiz_type: str = Field(..., description="multiple_choice, fill_in_blank, matching_heading")
    question: str = Field(...)
    options: Optional[List[str]] = Field(default=None, description="Only for multiple_choice")
    correct_answer: str = Field(...)
    
    # [QUAN TRỌNG] Lazy Explanation: Mặc định là None, chỉ gen khi User bấm nút "Giải thích"
    explanation: Optional[str] = Field(default=None, description="Generated later on-demand")
    
    # IELTS Psychometrics Traceability
    target_chunk_ids: List[str] = Field(..., description="List of chunk IDs this question belongs to")
    supporting_text: str = Field(..., description="Verbatim sentence from the text containing the answer")

# ==========================================
# 3. EXAM CLASS & MAIN MONGO SCHEMA 
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
    
    # Đã xóa analysis_review vì Master Planner không còn xuất ra text dư thừa
    chunks: List[ArticleChunk] = Field(default_factory=list)
    exams: List[Exam] = Field(default_factory=list) 
    
    status: str = Field(default="pending")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }