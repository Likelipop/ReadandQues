from typing import List, Dict, Any, Union, Optional
from typing_extensions import TypedDict
import random
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field

from .config import get_llm

# --- A. STATE & TỐI GIẢN SCHEMAS ---
class GraphState(TypedDict):
    original_text: str
    paragraphs: List[str]           
    exam_config: Dict[str, Any]     # VD: {"total_questions": 14, "hard_questions": 7}
    
    # 1. Output của Node Planner (Thay thế cho Node A & C cũ)
    master_plan: Dict[str, Any]     
    
    # 2. Output của Node Chunker (Code thuần Python)
    chunks: List[Dict[str, Any]]    
    
    # 3. Output của các Node Sinh Câu Hỏi (Chạy song song)
    mcq_quizzes: List[Dict[str, Any]]
    fib_quizzes: List[Dict[str, Any]]
    # matching_quizzes: List[...] <-- Dễ dàng thêm ở đây sau này
    
    # 4. Output cuối cùng
    final_exam: Dict[str, Any]

# --- PYDANTIC SCHEMAS (ÉP KIỂU TRẢ VỀ SIÊU NHỎ GỌN) ---
class ChunkInstruction(BaseModel):
    chunk_id: str = Field(..., description="e.g., chunk_1")
    paragraph_indices: List[int] = Field(..., description="Indices of paragraphs to group. e.g., [0, 1]")
    main_idea: str = Field(..., description="Short 5-word summary of this chunk")

class QuestionPlanItem(BaseModel):
    id: str = Field(..., description="e.g., q_1")
    quiz_type: str = Field(..., description="multiple_choice, fill_in_blank, etc.")
    target_chunk_ids: List[str] = Field(..., description="Which chunk(s) this question is based on.")
    attendWhat: str = Field(..., description="Specific trick or focus (e.g., 'Test the contrast word', 'Focus on dates'). KEEP IT SHORT.")

class MasterPlanOutput(BaseModel):
    chunk_instructions: List[ChunkInstruction]
    question_plans: List[QuestionPlanItem]

class QuizItem(BaseModel):
    quiz_type: str = Field(..., description="multiple_choice or fill_in_blank")
    question: str = Field(...)
    options: Optional[List[str]] = Field(default=None, description="Only for multiple_choice")
    correct_answer: str = Field(...)
    explanation: str = Field(...)
    
    # IELTS Psychometrics Traceability
    source_chunk_ids: Union[List[str], str] = Field(..., description="IDs of chunks or -1 for whole passage")
    supporting_text: str = Field(..., description="Verbatim sentence from the text")

class QuizOutput(BaseModel):
    # Dùng chung cho tất cả các Node sinh câu hỏi
    quizzes: List[QuizItem]  # Dùng QuizItem schema thay vì Dict để hỗ trợ structured output chính xác


# --- B. THỰC THI CÁC NODES ---

def node_master_planner(state: GraphState) -> Dict[str, Any]:
    """
    Node 1 (LLM): Đọc toàn bộ văn bản 1 lần duy nhất.
    Suy nghĩ trong Context Window -> Trả ra cách cắt Text + Ma trận phân bổ đề thi.
    """
    llm = get_llm()
    structured_llm = llm.with_structured_output(MasterPlanOutput, method="function_calling")
    
    indexed_paragraphs = "\n".join([f"[{i}] {p}" for i, p in enumerate(state["paragraphs"])])
    config = state["exam_config"]
    
    prompt = f"""
    You are a Master IELTS Architect. Read these paragraphs:
    {indexed_paragraphs}
    
    Exam Requirement: Create exactly {config['total_questions']} questions ({config.get('hard_questions', 0)} hard).
    
    Tasks (Do not explain, just output the JSON):
    1. chunk_instructions: Group paragraphs into logical chunks using their indices. Assign a short main idea.
    2. question_plans: Distribute the required number of questions across these chunks. 
       - Mix 'multiple_choice' and 'fill_in_blank'.
       - Use 'attendWhat' to specify the exact trap or vocabulary focus.
    """
    result = structured_llm.invoke(prompt)
    return {"master_plan": result.model_dump()}


def node_chunker(state: GraphState) -> Dict[str, Any]:
    """
    Node 2 (Python thuần): Dùng chỉ thị từ Planner để cắt text vật lý.
    KHÔNG tốn API Token.
    """
    raw_paragraphs = state["paragraphs"]
    instructions = state["master_plan"]["chunk_instructions"]
    
    built_chunks = []
    for inst in instructions:
        content = "\n\n".join([raw_paragraphs[i] for i in inst["paragraph_indices"] if i < len(raw_paragraphs)])
        built_chunks.append({
            "chunk_id": inst["chunk_id"],
            "content": content,
            "source_paragraph_indices": inst["paragraph_indices"],
            "metadata": {
                "difficulty": "medium",
                "main_idea": inst["main_idea"],
                "keywords": []
            }
        })
        
    return {"chunks": built_chunks}


def node_mcq(state: GraphState) -> Dict[str, Any]:
    """
    Node 3a (LLM): Sinh Multiple Choice.
    TỐI ƯU TOKEN: Chỉ truyền vào đúng các Chunk được giao nhiệm vụ MCQ.
    """
    plans = state["master_plan"]["question_plans"]
    mcq_plans = [p for p in plans if p["quiz_type"] == "multiple_choice"]
    if not mcq_plans: return {"mcq_quizzes": []}
    
    # Chỉ trích xuất các Chunk liên quan đến MCQ để tiết kiệm Input Token
    target_ids = {chunk_id for plan in mcq_plans for chunk_id in plan["target_chunk_ids"]}
    relevant_chunks = [c for c in state["chunks"] if c["chunk_id"] in target_ids]
    
    llm = get_llm()
    structured_llm = llm.with_structured_output(QuizOutput, method="function_calling")
    
    prompt = f"""
    You are an expert IELTS Item Writer. Write high-quality Multiple Choice Questions (MCQs) for the following plans:
    {mcq_plans}
    
    Source Material (ONLY reference these chunks):
    {relevant_chunks}
    
    CRITICAL RULES FOR MULTIPLE CHOICE OPTIONS:
    1. Length and Style Balance:
       - All 4 options (the correct answer and the 3 distractors) must be of similar length (roughly equal word count).
       - Ensure the correct answer is NOT significantly longer or more detailed than the distractors, to avoid giving away the answer.
       - Use similar grammatical structures and complexity for all options.
    
    2. Distractor Design Formula (You MUST generate exactly 3 distractors using these specific rules):
       - Distractor 1 (70% Semantic Overlap): Matches about 70% of the meaning or core idea of the correct answer, but introduces a subtle, critical logical error, negation, or minor distortion of detail that makes it incorrect.
       - Distractor 2 (20% Text Association): Uses keywords, phrases, or facts directly present in the source text, but in a different context, making it factually incorrect for the specific question.
       - Distractor 3 (10% Semantic Near-Synonym): Uses near-synonyms of keywords in the correct answer that seem plausible but are incorrect/inaccurate when placed in the specific context of the sentence (e.g., using "complete" instead of "success", or similar contextual nuance). The selection of this near-synonym must show deep contextual understanding of the text.
    
    3. Traps and Correctness:
       - Execute the 'attendWhat' trap precisely for each question.
       - The 'correct_answer' must be factually correct based ONLY on the provided source material, and must be one of the choices in the 'options' list.
       - Include the correct answer in the 'options' list, along with the 3 distractors, in a random/shuffled order.
    """
    result = structured_llm.invoke(prompt)
    return {"mcq_quizzes": result.quizzes}


def node_fib(state: GraphState) -> Dict[str, Any]:
    """
    Node 3b (LLM): Sinh Fill in the Blank.
    TỐI ƯU TOKEN: Chỉ truyền vào đúng các Chunk được giao nhiệm vụ FIB.
    """
    plans = state["master_plan"]["question_plans"]
    fib_plans = [p for p in plans if p["quiz_type"] == "fill_in_blank"]
    if not fib_plans: return {"fib_quizzes": []}
    
    # Lọc Chunk tương tự MCQ
    target_ids = {chunk_id for plan in fib_plans for chunk_id in plan["target_chunk_ids"]}
    relevant_chunks = [c for c in state["chunks"] if c["chunk_id"] in target_ids]
    
    llm = get_llm()
    structured_llm = llm.with_structured_output(QuizOutput, method="function_calling")
    
    prompt = f"""
    You are an IELTS Sentence Completion Designer. Write Fill-in-the-Blank questions for:
    {fib_plans}
    
    Source Material:
    {relevant_chunks}
    
    Rules:
    1. Paraphrase the question heavily.
    2. The answer MUST be an exact word from the source chunk.
    """
    result = structured_llm.invoke(prompt)
    return {"fib_quizzes": result.quizzes}


def node_packager(state: GraphState) -> Dict[str, Any]:
    """Node 4 (Python thuần): Gom tất cả câu hỏi lại thành đề hoàn chỉnh."""
    all_quizzes = state.get("mcq_quizzes", []) + state.get("fib_quizzes", [])
    # Xáo trộn câu hỏi nếu cần
    random.shuffle(all_quizzes)
    
    exam_payload = {
        "exam_id": f"EXAM_{random.randint(1000, 9999)}",
        "total_questions": len(all_quizzes),
        "quizzes": all_quizzes
    }
    return {"final_exam": exam_payload}


# --- C. BUILD TOPOLOGY (ĐỒ THỊ DẠNG TỎA NHÁNH SONG SONG) ---
workflow = StateGraph(GraphState)

workflow.add_node("node_master_planner", node_master_planner)
workflow.add_node("node_chunker", node_chunker)
workflow.add_node("node_mcq", node_mcq)
workflow.add_node("node_fib", node_fib)
workflow.add_node("node_packager", node_packager)

# Luồng chính 1 đường thẳng
workflow.add_edge(START, "node_master_planner")
workflow.add_edge("node_master_planner", "node_chunker")

# Tỏa nhánh (Fan-out) ra các Generator Models (Chạy BẤT ĐỒNG BỘ SONG SONG)
workflow.add_edge("node_chunker", "node_mcq")
workflow.add_edge("node_chunker", "node_fib")

# Hội tụ (Fan-in) về Packager
workflow.add_edge("node_mcq", "node_packager")
workflow.add_edge("node_fib", "node_packager")
workflow.add_edge("node_packager", END)

app = workflow.compile()