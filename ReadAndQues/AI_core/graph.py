"""
ReadAndQues/AI_core/graph.py — 4-node LangGraph pipeline for IELTS exam generation.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from langgraph.graph import END, START, StateGraph

from .config import ExamConfig, get_llm
from .prompts import build_analysis_prompt, build_question_prompt, build_verifier_prompt
from .schemas import (
    ExamOutput,
    GraphState,
    SemanticAnalysis,
    TokenUsageLog,
    VerifierFeedback,
)

MAX_RETRIES = 2


def _extract_token_usage(raw_message: Any) -> Dict[str, int]:
    usage = getattr(raw_message, "usage_metadata", None) or {}
    return {
        "input_tokens":  usage.get("input_tokens",  0),
        "output_tokens": usage.get("output_tokens", 0),
    }


def _append_token_log(
    state_log: List[Dict[str, Any]],
    node: str,
    raw_message: Any,
) -> List[Dict[str, Any]]:
    usage = _extract_token_usage(raw_message)
    entry = TokenUsageLog(
        node=node,
        input_tokens=usage["input_tokens"],
        output_tokens=usage["output_tokens"],
    )
    return state_log + [entry.model_dump()]


def node_analyzer(state: GraphState) -> Dict[str, Any]:
    text = state["original_text"]
    prompt = build_analysis_prompt(text)

    llm = get_llm(temperature=0.0)
    structured_llm = llm.with_structured_output(
        SemanticAnalysis, include_raw=True, method="function_calling"
    )
    raw_result = structured_llm.invoke(prompt)

    parsed: SemanticAnalysis = raw_result["parsed"]
    token_log = _append_token_log(
        state.get("token_log", []), "analyzer", raw_result["raw"]
    )

    config = ExamConfig.from_text(text)

    return {
        "semantic_analysis": parsed.model_dump(),
        "exam_config":       config.model_dump(),
        "token_log":         token_log,
        "retry_count":       0,
    }


def node_text_cleaner(state: GraphState) -> Dict[str, Any]:
    text = state["original_text"]
    analysis = state.get("semantic_analysis", {})
    snippets = analysis.get("irrelevant_snippets", [])

    for snippet in snippets:
        if snippet and snippet in text:
            text = text.replace(snippet, "").strip()

    return {"original_text": text}


def node_question_planner(state: GraphState) -> Dict[str, Any]:
    text     = state["original_text"]
    analysis = state["semantic_analysis"]
    config   = ExamConfig(**state["exam_config"])

    prompt = build_question_prompt(text, analysis, config)

    llm = get_llm(temperature=0.3)
    structured_llm = llm.with_structured_output(
        ExamOutput, include_raw=True, method="function_calling"
    )
    raw_result = structured_llm.invoke(prompt)

    parsed: ExamOutput = raw_result["parsed"]
    token_log = _append_token_log(
        state.get("token_log", []), "question_planner", raw_result["raw"]
    )

    return {
        "raw_quizzes": [q.model_dump() for q in parsed.quizzes],
        "token_log":   token_log,
    }


def node_verifier(state: GraphState) -> Dict[str, Any]:
    text    = state["original_text"]
    quizzes = state.get("raw_quizzes", [])

    prompt = build_verifier_prompt(text, quizzes)

    llm = get_llm(temperature=0.0)
    structured_llm = llm.with_structured_output(
        VerifierFeedback, include_raw=True, method="function_calling"
    )
    raw_result = structured_llm.invoke(prompt)

    feedback: VerifierFeedback = raw_result["parsed"]
    token_log = _append_token_log(
        state.get("token_log", []), "verifier", raw_result["raw"]
    )
    retry_count = state.get("retry_count", 0)

    if feedback.passed or retry_count >= MAX_RETRIES:
        verified = quizzes
    else:
        verified = [q for i, q in enumerate(quizzes) if i not in feedback.rejected_indices]
        retry_count += 1

    return {
        "verified_quizzes": verified,
        "retry_count":      retry_count,
        "token_log":        token_log,
        "_verifier_passed": feedback.passed or retry_count >= MAX_RETRIES,
    }


def node_formatter(state: GraphState) -> Dict[str, Any]:
    quizzes   = state.get("verified_quizzes", [])
    token_log = state.get("token_log", [])

    final_exam = {
        "exam_id":         f"EXAM_{uuid.uuid4().hex[:12].upper()}",
        "title":           "IELTS Academic Reading Test",
        "total_questions": len(quizzes),
        "quizzes":         quizzes,
        "token_usage":     token_log,
        "created_at":      datetime.now(timezone.utc).isoformat(),
    }

    return {"final_exam": final_exam}


def route_after_verifier(state: GraphState) -> str:
    if state.get("_verifier_passed", True):
        return "formatter"
    return "question_planner"


workflow = StateGraph(GraphState)

workflow.add_node("analyzer",          node_analyzer)
workflow.add_node("text_cleaner",      node_text_cleaner)
workflow.add_node("question_planner",  node_question_planner)
workflow.add_node("verifier",          node_verifier)
workflow.add_node("formatter",         node_formatter)

workflow.add_edge(START,              "analyzer")
workflow.add_edge("analyzer",         "text_cleaner")
workflow.add_edge("text_cleaner",     "question_planner")
workflow.add_edge("question_planner", "verifier")
workflow.add_conditional_edges(
    "verifier",
    route_after_verifier,
    {
        "question_planner": "question_planner",
        "formatter":        "formatter",
    },
)
workflow.add_edge("formatter", END)

app = workflow.compile()
