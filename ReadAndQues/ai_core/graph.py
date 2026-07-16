from typing import List, Dict, Any, Union
from typing_extensions import TypedDict
import random
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field
from ai_core.config import get_llm
from articles.models import QuizItem, ArticleChunk, ChunkMetadata

# --- A. State & Internal Schemas ---
class GraphState(TypedDict):
    original_text: str
    paragraphs: List[str]           # Split by \n\n beforehand
    exam_config: Dict[str, Any]     # e.g., {"total": 14, "hard": 7}
    
    # Node A Outputs
    article_analysis: Dict[str, Any] 
    
    # Node B Outputs
    chunks: List[Dict[str, Any]]    # Dictionaries of ArticleChunk
    
    # Node C Outputs
    question_plan: List[Dict[str, Any]]
    
    # Node D & E Outputs
    mcq_quizzes: List[Dict[str, Any]]
    fib_quizzes: List[Dict[str, Any]]
    
    # Node F Output
    final_exam: Dict[str, Any]

# Pydantic cho Node A (Phân tích)
class ChunkInstruction(BaseModel):
    chunk_id: str = Field(..., description="e.g., chunk_1")
    paragraph_indices: List[int] = Field(..., description="List of indices from the raw paragraphs array to group together")
    main_idea: str = Field(...)
    keywords: List[str] = Field(...)
    difficulty: str = Field(..., description="easy, medium, or hard")

class ArticleAnalysisOutput(BaseModel):
    main_idea_overall: str
    keywords_overall: List[str]
    examiner_review: str = Field(..., description="Detailed review of text difficulty, complex grammar, and potential trap areas.")
    chunk_instructions: List[ChunkInstruction]

# Pydantic cho Node C (Lên kế hoạch)
class QuestionPlanItem(BaseModel):
    id: str = Field(..., description="Unique ID for this question plan")
    quiz_type: str = Field(..., description="multiple_choice or fill_in_blank")
    attendWhere: Union[List[str], int] = Field(..., description="List of chunk_ids, or -1 for the whole article")
    attendWhat: str = Field(..., description="Specific instructions, trap ideas, or vocabulary/grammar focus for the generators")
    difficulty: str = Field(...)

class QuestionPlanOutput(BaseModel):
    plans: List[QuestionPlanItem]

class QuizOutput(BaseModel):
    quizzes: List[QuizItem]


# --- B. Nodes Implementation ---

def node_a_analyze(state: GraphState) -> Dict[str, Any]:
    """Node A: Analyzes the text and creates chunking instructions."""
    llm = get_llm()
    structured_llm = llm.with_structured_output(ArticleAnalysisOutput)
    
    # Prepare raw paragraphs with indices for the LLM to map
    indexed_paragraphs = "\n".join([f"[{i}] {p}" for i, p in enumerate(state["paragraphs"])])
    
    prompt = f"""
    You are an Expert IELTS Examiner. Read the following paragraphs:
    {indexed_paragraphs}
    
    Tasks:
    1. Provide the overall main idea and keywords.
    2. Write an 'examiner_review' detailing the text's difficulty, tricky syntax, and vocabulary.
    3. Group related paragraphs into logical 'chunks' using their indices [0], [1], etc. Provide a main idea and keywords for each chunk.
    """
    result = structured_llm.invoke(prompt)
    return {"article_analysis": result.model_dump()}


def node_b_chunking(state: GraphState) -> Dict[str, Any]:
    """Node B: Pure Python node that physically builds the chunks based on Node A's instructions."""
    raw_paragraphs = state["paragraphs"]
    analysis = state["article_analysis"]
    
    built_chunks = []
    for inst in analysis["chunk_instructions"]:
        # Group text using the indices provided by the LLM
        content = "\n\n".join([raw_paragraphs[i] for i in inst["paragraph_indices"] if i < len(raw_paragraphs)])
        
        chunk = ArticleChunk(
            chunk_id=inst["chunk_id"],
            content=content,
            source_paragraph_indices=inst["paragraph_indices"],
            metadata=ChunkMetadata(
                difficulty=inst["difficulty"],
                main_idea=inst["main_idea"],
                keywords=inst["keywords"]
            )
        )
        built_chunks.append(chunk.model_dump())
        
    return {"chunks": built_chunks}


def node_c_planner(state: GraphState) -> Dict[str, Any]:
    """Node C: Uses ExamConfig and Analysis to generate a strategic question matrix."""
    llm = get_llm()
    structured_llm = llm.with_structured_output(QuestionPlanOutput)
    
    config = state["exam_config"]
    analysis = state["article_analysis"]
    chunks_info = [{"id": c["chunk_id"], "idea": c["metadata"]["main_idea"]} for c in state["chunks"]]
    
    prompt = f"""
    As an IELTS Test Designer, create a question plan.
    Exam Config: Generate exactly {config['total_questions']} questions ({config['hard_questions']} must be 'hard').
    
    Examiner Review: {analysis['examiner_review']}
    Available Chunks: {chunks_info}
    
    Create a mix of 'multiple_choice' and 'fill_in_blank'.
    For 'attendWhere', specify the chunk_id(s) or -1 for general questions.
    For 'attendWhat', provide specific hints (e.g., 'Test understanding of keyword X', 'Create a trap around the author's tone').
    """
    result = structured_llm.invoke(prompt)
    return {"question_plan": [plan.model_dump() for plan in result.plans]}


def node_d_mcq(state: GraphState) -> Dict[str, Any]:
    """Node D: Generates MCQs based strictly on the planner's attendWhat hints."""
    mcq_plans = [p for p in state["question_plan"] if p["quiz_type"] == "multiple_choice"]
    if not mcq_plans: return {"mcq_quizzes": []}
    
    llm = get_llm()
    structured_llm = llm.with_structured_output(QuizOutput)
    
    prompt = f"""
    You are an IELTS Item Writer. Generate Multiple Choice Questions based on these plans:
    {mcq_plans}
    
    Available Text Chunks: {state['chunks']}
    Examiner Context: {state['article_analysis']['examiner_review']}
    
    RULES:
    1. Distractor Formula: 70% overlap (false twist), 10% not in text, 10% wrong context.
    2. Keep option lengths balanced.
    3. Strictly follow the 'attendWhat' instructions for each plan.
    """
    result = structured_llm.invoke(prompt)
    return {"mcq_quizzes": [q.model_dump() for q in result.quizzes]}


def node_e_fib(state: GraphState) -> Dict[str, Any]:
    """Node E: Generates Fill-in-the-Blank questions with heavy paraphrasing."""
    fib_plans = [p for p in state["question_plan"] if p["quiz_type"] == "fill_in_blank"]
    if not fib_plans: return {"fib_quizzes": []}
    
    llm = get_llm()
    structured_llm = llm.with_structured_output(QuizOutput)
    
    prompt = f"""
    You are an IELTS Sentence Completion Designer. Generate FIB questions based on these plans:
    {fib_plans}
    
    Available Text Chunks: {state['chunks']}
    Examiner Context: {state['article_analysis']['examiner_review']}
    
    RULES:
    1. Paraphrase the question heavily.
    2. The 'correct_answer' MUST be an exact word/phrase present in the source chunk.
    3. Strictly follow the 'attendWhat' instructions.
    """
    result = structured_llm.invoke(prompt)
    return {"fib_quizzes": [q.model_dump() for q in result.quizzes]}


def node_f_packager(state: GraphState) -> Dict[str, Any]:
    """Node F: Aggregates and finalizes the exam."""
    all_quizzes = state.get("mcq_quizzes", []) + state.get("fib_quizzes", [])
    random.shuffle(all_quizzes)
    
    exam_payload = {
        "exam_id": f"EXAM_{random.randint(1000, 9999)}",
        "title": "IELTS Reading Practice (Agentic Generated)",
        "total_questions": len(all_quizzes),
        "quizzes": all_quizzes
    }
    return {"final_exam": exam_payload}


# --- C. Build Topology ---
workflow = StateGraph(GraphState)

workflow.add_node("node_a_analyze", node_a_analyze)
workflow.add_node("node_b_chunking", node_b_chunking)
workflow.add_node("node_c_planner", node_c_planner)
workflow.add_node("node_d_mcq", node_d_mcq)
workflow.add_node("node_e_fib", node_e_fib)
workflow.add_node("node_f_packager", node_f_packager)

workflow.add_edge(START, "node_a_analyze")
workflow.add_edge("node_a_analyze", "node_b_chunking")
workflow.add_edge("node_b_chunking", "node_c_planner")

# Fan-out to Question Generators
workflow.add_edge("node_c_planner", "node_d_mcq")
workflow.add_edge("node_c_planner", "node_e_fib")

# Fan-in to Packager
workflow.add_edge("node_d_mcq", "node_f_packager")
workflow.add_edge("node_e_fib", "node_f_packager")
workflow.add_edge("node_f_packager", END)

app = workflow.compile()