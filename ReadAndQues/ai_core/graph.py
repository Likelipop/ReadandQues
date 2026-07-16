from typing import Dict, Any, List
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field
from ai_core.config import get_llm
from ai_core.schemas import ArticleAnalysis, QuizItem

# 1. Định nghĩa State (Trạng thái truyền dữ liệu xuyên suốt các Node)
class GraphState(TypedDict):
    original_text: str
    is_safe: bool
    status_reason: str
    analysis: Dict[str, Any]
    quizzes: List[Dict[str, Any]]

# Schema Pydantic phụ trợ cho lớp Guardrail bảo vệ
class GuardrailOutput(BaseModel):
    is_safe: bool = Field(..., description="True nếu bài báo an toàn, False nếu chứa nội dung chính trị độc hại, chiến tranh, nhạy cảm")
    reason: str = Field(..., description="Lý do ngắn gọn tại sao an toàn hoặc không an toàn")

# Schema Pydantic bọc ngoài danh sách câu hỏi để ép kiểu list dễ dàng hơn
class QuizListOutput(BaseModel):
    quizzes: List[QuizItem] = Field(..., description="Danh sách các câu hỏi quiz được tạo ra")

# 2. Định nghĩa các Nodes xử lý logic
def guardrail_filter(state: GraphState) -> Dict[str, Any]:
    llm = get_llm()
    # Ép kiểu cấu trúc đầu ra cho LLM chuyên trách check lỗi
    structured_llm = llm.with_structured_output(GuardrailOutput)
    
    prompt = f"""Bạn là một hệ thống kiểm duyệt nội dung giáo dục. Hãy phân tích bài báo sau đây.
    Nếu bài báo chứa nội dung nhạy cảm liên quan đến chính trị cực đoan, 
    chiến tranh, tuyên truyền kích động hoặc đồi trụy, 
    hãy đánh giá là KHÔNG an toàn (is_safe = False).
    Bài báo: {state['original_text']}"""
    
    result = structured_llm.invoke(prompt)
    return {"is_safe": result.is_safe, "status_reason": result.reason}

def analyze_article(state: GraphState) -> Dict[str, Any]:
    # Nếu dính guardrail, không chạy tiếp logic AI nặng
    if not state.get("is_safe", True):
        return {}
        
    llm = get_llm()
    structured_llm = llm.with_structured_output(ArticleAnalysis)
    
    prompt = f"""Bạn là một chuyên gia ngôn ngữ Anh. Hãy đọc bài báo dưới đây và thực hiện phân tích chi tiết:
    1. Tìm ý chính (main_idea).
    2. Tóm tắt ngắn gọn từng đoạn văn.
    3. Lọc ra các từ khóa (keywords).
    4. Trích xuất danh sách từ vựng hay/khó kèm từ loại, nghĩa trong ngữ cảnh và câu ví dụ.
    5. Chỉ ra các cấu trúc ngữ pháp đáng chú ý xuất hiện trong bài báo.
    
    Bài báo: {state['original_text']}"""
    
    result = structured_llm.invoke(prompt)
    # Convert Pydantic object sang Dict để đẩy vào State của LangGraph
    return {"analysis": result.model_dump()}

def generate_quizzes(state: GraphState) -> Dict[str, Any]:
    if not state.get("is_safe", True):
        return {}
        
    llm = get_llm()
    structured_llm = llm.with_structured_output(QuizListOutput)
    
    # Lấy dữ liệu từ vựng vừa phân tích từ Node trước để làm gợi ý ra đề cho sát bài học
    vocab_list = [v['word'] for v in state['analysis'].get('vocabularies', [])]
    
    prompt = f"""Bạn là một giáo viên tiếng Anh thiết kế đề thi đọc hiểu. 
    Dựa trên nội dung bài báo và danh sách từ vựng trọng tâm này: {vocab_list}.
    Hãy tạo ra một bộ câu hỏi quiz kiểm tra năng lực đọc hiểu (đầy đủ các loại: multiple_choice, fill_in_blank, matching...).
    Với mỗi câu hỏi trắc nghiệm, bắt buộc phải có đủ trường 'options'. Với câu hỏi điền từ hoặc nối từ, có thể bỏ trống trường này nếu không cần thiết.
    Nhớ kèm theo giải thích (explanation) lý do đáp án đó đúng.
    
    Bài báo: {state['original_text']}"""
    
    result = structured_llm.invoke(prompt)
    return {"quizzes": [q.model_dump() for q in result.quizzes]}

# 3. Định nghĩa hàm rẽ nhánh điều hướng (Conditional Edge)
def decide_next_step(state: GraphState) -> str:
    if state.get("is_safe", True):
        return "analyze_article"
    return "end_workflow"

# 4. Lắp ráp Đồ thị LangGraph
workflow = StateGraph(GraphState)

# Thêm các Node
workflow.add_node("guardrail_filter", guardrail_filter)
workflow.add_node("analyze_article", analyze_article)
workflow.add_node("generate_quizzes", generate_quizzes)

# Thiết lập Luồng đi (Edges)
workflow.add_edge(START, "guardrail_filter")

# Rẽ nhánh dựa trên kết quả Guardrail
workflow.add_conditional_edges(
    "guardrail_filter",
    decide_next_step,
    {
        "analyze_article": "analyze_article",
        "end_workflow": END
    }
)

workflow.add_edge("analyze_article", "generate_quizzes")
workflow.add_edge("generate_quizzes", END)

# Biên dịch ứng dụng đồ thị
app = workflow.compile()