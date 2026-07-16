from typing import List, Dict, Any
from typing_extensions import TypedDict
import random
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field
from ai_core.config import get_llm
from ai_core.schemas import QuizItem

# 1. StateGraph State definition
class GraphState(TypedDict):
    original_text: str
    chunks: List[Dict[str, Any]]
    total_target_questions: int
    hard_target_count: int
    question_plan: List[Dict[str, Any]]
    mcq_quizzes: List[Dict[str, Any]] # Written by quiz_node
    fib_quizzes: List[Dict[str, Any]] # Written by fill_in_the_blank_node
    final_exam: Dict[str, Any]

# --- Pydantic Output Structuring Schemas ---
class QuestionPlanItem(BaseModel):
    quiz_type: str = Field(..., description="Must be 'multiple_choice' or 'fill_in_blank'")
    target_chunk_id: str = Field(..., description="Chunk ID targeted for the question")
    difficulty: str = Field(..., description="Must be 'easy', 'medium', or 'hard'")

class QuestionPlanOutput(BaseModel):
    plans: List[QuestionPlanItem]

class MCQOutput(BaseModel):
    quizzes: List[QuizItem]

class FIBOutput(BaseModel):
    quizzes: List[QuizItem]


# --- Nodes Implementation ---

def chunk_and_analyze(state: GraphState) -> Dict[str, Any]:
    """Helper to split raw article into standard paragraphs and assign metadata."""
    paragraphs = [p.strip() for p in state["original_text"].split("\n\n") if p.strip()]
    analyzed_chunks = []
    
    for idx, content in enumerate(paragraphs):
        chunk_id = f"chunk_{idx + 1}"
        difficulty = "hard" if idx % 2 == 0 else "easy" if idx % 3 == 0 else "medium"
        analyzed_chunks.append({
            "chunk_id": chunk_id,
            "content": content,
            "paragraph_number": idx + 1,
            "metadata": {
                "difficulty": difficulty,
                "contains_vocabulary": len(content) > 150,
                "contains_numbers": any(char.isdigit() for char in content),
                "contains_grammar": True
            }
        })
    return {"chunks": analyzed_chunks}


def question_planner(state: GraphState) -> Dict[str, Any]:
    """Orchestrator Node: Strategically allocates difficulty and question types across chunks."""
    llm = get_llm()
    structured_llm = llm.with_structured_output(QuestionPlanOutput)
    
    chunks_catalog = [{"chunk_id": c["chunk_id"], "difficulty": c["metadata"]["difficulty"]} for c in state["chunks"]]
    total_q = state.get("total_target_questions", 14)
    hard_q = state.get("hard_target_count", 7)
    
    system_prompt = f"""
    You are an expert IELTS Reading Exam Director. 
    Your job is to allocate a strict matrix plan of questions based on this available catalog:
    {chunks_catalog}

    Total Questions to generate: {total_q}
    Total HARD Questions to generate: {hard_q}

    Strict Allocation Constraints:
    1. The output list MUST contain exactly {total_q} plans.
    2. Exactly {hard_q} of those plans MUST be assigned the 'hard' difficulty tier.
    3. The remaining {total_q - hard_q} plans must be randomly/strategically distributed between 'easy' and 'medium'.
    4. Balance the question types evenly between 'multiple_choice' and 'fill_in_blank'.
    """
    
    result = structured_llm.invoke(system_prompt)
    return {"question_plan": [item.model_dump() for item in result.plans]}


def quiz_node(state: GraphState) -> Dict[str, Any]:
    """MCQ Node: Builds high-validity IELTS MCQs with rigid distractor structures."""
    plans = [p for p in state["question_plan"] if p["quiz_type"] == "multiple_choice"]
    if not plans:
        return {"mcq_quizzes": []}
        
    llm = get_llm()
    structured_llm = llm.with_structured_output(MCQOutput)
    
    target_chunks = {p["target_chunk_id"] for p in plans}
    context_text = "\n\n".join([f"[{c['chunk_id']}]\n{c['content']}" for c in state["chunks"] if c["chunk_id"] in target_chunks])
    
    system_prompt = f"""
    You are an elite IELTS MCQ Item Writer.
    Analyze the following text chunks:
    {context_text}
    
    Generate questions strictly aligned with this allocation blueprint:
    {plans}
    
    STRICT DISTRACTOR FORMULA FOR THE 4 OPTIONS:
    - Correct Option: A perfect semantic paraphrase of the supporting text facts.
    - Distractor A (70% Overlap Bias): Retains 70% of exact wording/keywords from the chunk, but alters negation, relationship, or truth value to be factually false. Traps superficial matching readers.
    - Distractor B (10% Incorrect Fact): Direct logical contradiction of the passage details.
    - Distractor C (10% Absent Concept): Plausible-sounding details completely missing/unsupported by the text.
    - Distractor D (10% Wrong Context): Factually 100% correct according to the passage, but taken from a completely different chunk/paragraph than the targeted area of this question.

    CRITICAL QUALITY CONSTRAINT:
    The character length and syntax complexity of ALL 4 options within a question MUST be highly similar (+/- 10% maximum length variance). Never make the correct option the longest or most detailed.
    
    Each MCQ must contain the correct answer, step-by-step logic in the explanation, verbatim supporting_text, and character offsets.
    """
    
    result = structured_llm.invoke(system_prompt)
    return {"mcq_quizzes": [q.model_dump() for q in result.quizzes]}


def fill_in_the_blank_node(state: GraphState) -> Dict[str, Any]:
    """FIB Node: Creates sentence completions with heavy paraphrasing and literal original word blanks."""
    plans = [p for p in state["question_plan"] if p["quiz_type"] == "fill_in_blank"]
    if not plans:
        return {"fib_quizzes": []}
        
    llm = get_llm()
    structured_llm = llm.with_structured_output(FIBOutput)
    
    target_chunks = {p["target_chunk_id"] for p in plans}
    context_text = "\n\n".join([f"[{c['chunk_id']}]\n{c['content']}" for c in state["chunks"] if c["chunk_id"] in target_chunks])
    
    system_prompt = f"""
    You are an expert IELTS Sentence Completion Designer.
    Analyze the following text chunks:
    {context_text}
    
    Generate Fill-in-the-Blank items strictly matching this blueprint:
    {plans}
    
    STRICT IMPLEMENTATION RULES:
    1. Paraphrase the target chunk's context heavily. The question prompt must NOT copy-paste the sentence structure from the original text.
    2. The 'correct_answer' (blanked word) MUST be an exact keyword extracted directly from the targeted chunk without any spelling modifications.
    3. Self-Critique Step: Audit your question to guarantee that based ONLY on the targeted text context, the 'correct_answer' is the sole grammatically and logically correct fit.
    """
    
    result = structured_llm.invoke(system_prompt)
    return {"fib_quizzes": [q.model_dump() for q in result.quizzes]}


def exam_packager(state: GraphState) -> Dict[str, Any]:
    """Aggregates and formats the final Exam set, shuffling compiled questions."""
    compiled_quizzes = state.get("mcq_quizzes", []) + state.get("fib_quizzes", [])
    random.shuffle(compiled_quizzes)
    
    exam_payload = {
        "exam_id": f"EXAM_{random.randint(10000, 99999)}",
        "title": "IELTS Academic Reading Practice Test",
        "total_questions": len(compiled_quizzes),
        "quizzes": compiled_quizzes
    }
    return {"final_exam": exam_payload}


# --- Parallel Topology Construction ---
workflow = StateGraph(GraphState)

workflow.add_node("chunk_and_analyze", chunk_and_analyze)
workflow.add_node("question_planner", question_planner)
workflow.add_node("quiz_node", quiz_node)
workflow.add_node("fill_in_the_blank_node", fill_in_the_blank_node)
workflow.add_node("exam_packager", exam_packager)

# Routing Edges
workflow.add_edge(START, "chunk_and_analyze")
workflow.add_edge("chunk_and_analyze", "question_planner")

# Parallel Execution Trigger (Fan-out)
workflow.add_edge("question_planner", "quiz_node")
workflow.add_edge("question_planner", "fill_in_the_blank_node")

# Convergence Trigger (Fan-in)
workflow.add_edge("quiz_node", "exam_packager")
workflow.add_edge("fill_in_the_blank_node", "exam_packager")

workflow.add_edge("exam_packager", END)

app = workflow.compile()