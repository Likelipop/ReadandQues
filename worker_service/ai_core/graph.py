"""
ai_core/graph.py — 4-node LangGraph pipeline for IELTS exam generation.

Pipeline:
  analyzer  →  question_planner  →  verifier  ──(pass / max_retries)──→  formatter → END
                    ↑___________________(retry, max 2)___|

Node roles:
  1. analyzer         (LLM) — deep semantic analysis + genre classification
  2. question_planner (LLM) — generate YNNG + FIB + MCQ questions grounded in analysis
  3. verifier         (LLM) — check each question is verbatim-grounded; route to retry or pass
  4. formatter        (pure Python) — build final Exam document, embed token_log, assign UUID
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List

from langgraph.graph import END, START, StateGraph

from .config import ExamConfig, get_llm
from .prompts import (build_analysis_prompt, build_question_prompt,
                      build_verifier_prompt)
from .schemas import (ExamOutput, GraphState, SemanticAnalysis, TokenUsageLog,
                      VerifierFeedback)

MAX_RETRIES = 2


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _extract_token_usage(raw_message: Any) -> Dict[str, int]:
    """Pull input/output token counts from a raw LLM message."""
    usage = getattr(raw_message, "usage_metadata", None) or {}
    return {
        "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
    }


def _append_token_log(
    state_log: List[Dict[str, Any]],
    node: str,
    raw_message: Any,
) -> List[Dict[str, Any]]:
    """Return a new token_log list with the current node's usage appended."""
    usage = _extract_token_usage(raw_message)
    entry = TokenUsageLog(
        node=node,
        input_tokens=usage["input_tokens"],
        output_tokens=usage["output_tokens"],
    )
    return state_log + [entry.model_dump()]


# ──────────────────────────────────────────────────────────────────────────────
# Node 1 — Analyzer
# ──────────────────────────────────────────────────────────────────────────────


def node_analyzer(state: GraphState) -> Dict[str, Any]:
    """
    Classify genre and perform deep semantic analysis of the article.
    Output: semantic_analysis (SemanticAnalysis.model_dump())
    """
    text = state["original_text"]
    prompt = build_analysis_prompt(text)

    llm = get_llm(
        temperature=0.0
    )  # deterministic — genre classification must be stable
    structured_llm = llm.with_structured_output(
        SemanticAnalysis, include_raw=True, method="function_calling"
    )
    raw_result = structured_llm.invoke(prompt)

    parsed: SemanticAnalysis = raw_result["parsed"]
    token_log = _append_token_log(
        state.get("token_log", []), "analyzer", raw_result["raw"]
    )

    # Build ExamConfig based on text length
    config = ExamConfig.from_text(text)

    print(
        f"[analyzer] Genre: {parsed.genre} | "
        f"Tokens in={token_log[-1]['input_tokens']} out={token_log[-1]['output_tokens']}"
    )

    return {
        "semantic_analysis": parsed.model_dump(),
        "exam_config": config.model_dump(),
        "token_log": token_log,
        "retry_count": 0,  # initialise retry counter here
    }


# ──────────────────────────────────────────────────────────────────────────────
# Node 1.5 — Text Cleaner
# ──────────────────────────────────────────────────────────────────────────────


def node_text_cleaner(state: GraphState) -> Dict[str, Any]:
    """
    Remove irrelevant snippets (ads, boilerplate) identified by the analyzer.
    Outputs: original_text (cleaned version)
    """
    text = state["original_text"]
    analysis = state.get("semantic_analysis", {})
    snippets = analysis.get("irrelevant_snippets", [])

    removed_count = 0
    for snippet in snippets:
        if snippet and snippet in text:
            # Replace verbatim snippet with empty string (and strip extra whitespace)
            text = text.replace(snippet, "").strip()
            removed_count += 1

    if removed_count > 0:
        print(f"[text_cleaner] Removed {removed_count} irrelevant snippets.")

    return {"original_text": text}


# ──────────────────────────────────────────────────────────────────────────────
# Node 2 — Question Planner
# ──────────────────────────────────────────────────────────────────────────────


def node_question_planner(state: GraphState) -> Dict[str, Any]:
    """
    Generate IELTS questions (YNNG + FIB + MCQ) grounded in the semantic analysis.
    Output: raw_quizzes (List[QuizItem.model_dump()])
    """
    text = state["original_text"]
    analysis = state["semantic_analysis"]
    config = ExamConfig(**state["exam_config"])

    prompt = build_question_prompt(text, analysis, config)

    llm = get_llm(temperature=1.0)  # creative — question variety matters
    structured_llm = llm.with_structured_output(
        ExamOutput, include_raw=True, method="function_calling"
    )
    raw_result = structured_llm.invoke(prompt)

    parsed = raw_result.get("parsed")
    if not parsed:
        print(f"[question_planner] Failed to parse output. Raw: {raw_result.get('raw')}")
        raise ValueError("Failed to parse ExamOutput from LLM")

    token_log = _append_token_log(
        state.get("token_log", []), "question_planner", raw_result["raw"]
    )

    print(
        f"[question_planner] Generated {len(parsed.quizzes)} questions | "
        f"Tokens in={token_log[-1]['input_tokens']} out={token_log[-1]['output_tokens']}"
    )

    return {
        "raw_quizzes": [q.model_dump() for q in parsed.quizzes],
        "token_log": token_log,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Node 3 — Verifier
# ──────────────────────────────────────────────────────────────────────────────


def node_verifier(state: GraphState) -> Dict[str, Any]:
    """
    Verify that every question is verbatim-grounded in the article.
    - If passed (or max retries reached): write verified_quizzes and move to formatter.
    - If failed and retries remain: increment retry_count and return to question_planner.
    Output: verified_quizzes, retry_count, token_log
    """
    text = state["original_text"]
    quizzes = state.get("raw_quizzes", [])

    prompt = build_verifier_prompt(text, quizzes)

    llm = get_llm(temperature=0.0)  # deterministic — strict grounding verification
    structured_llm = llm.with_structured_output(
        VerifierFeedback, include_raw=True, method="function_calling"
    )
    raw_result = structured_llm.invoke(prompt)

    feedback: VerifierFeedback = raw_result["parsed"]
    token_log = _append_token_log(
        state.get("token_log", []), "verifier", raw_result["raw"]
    )
    retry_count = state.get("retry_count", 0)

    print(
        f"[verifier] passed={feedback.passed} | "
        f"rejected={feedback.rejected_indices} | "
        f"retry_count={retry_count} | "
        f"Tokens in={token_log[-1]['input_tokens']} out={token_log[-1]['output_tokens']}"
    )

    if feedback.passed or retry_count >= MAX_RETRIES:
        # Accept as-is (either clean pass, or we've exhausted retries)
        if not feedback.passed:
            print(
                f"[verifier] ⚠️  Max retries reached — accepting with "
                f"{len(feedback.rejected_indices)} unresolved issues."
            )
        verified = quizzes
    else:
        # Remove the rejected questions so the planner can try again
        verified = [
            q for i, q in enumerate(quizzes) if i not in feedback.rejected_indices
        ]
        retry_count += 1

    return {
        "verified_quizzes": verified,
        "retry_count": retry_count,
        "token_log": token_log,
        # Store feedback for the router to inspect
        "_verifier_passed": feedback.passed or retry_count >= MAX_RETRIES,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Node 4 — Formatter  (no LLM)
# ──────────────────────────────────────────────────────────────────────────────


def node_formatter(state: GraphState) -> Dict[str, Any]:
    """
    Assemble the final Exam document.  No LLM call — pure data transformation.
    Output: final_exam (dict matching the Exam Pydantic model)
    """
    quizzes = state.get("verified_quizzes", [])
    token_log = state.get("token_log", [])

    final_exam = {
        "exam_id": f"EXAM_{uuid.uuid4().hex[:12].upper()}",
        "title": "IELTS Academic Reading Test",
        "total_questions": len(quizzes),
        "quizzes": quizzes,
        "token_usage": token_log,
        "created_at": datetime.utcnow().isoformat(),
    }

    print(f"[formatter] Exam {final_exam['exam_id']} — {len(quizzes)} questions")

    return {"final_exam": final_exam}


# ──────────────────────────────────────────────────────────────────────────────
# Conditional edge: verifier → question_planner | formatter
# ──────────────────────────────────────────────────────────────────────────────


def route_after_verifier(state: GraphState) -> str:
    """Return the next node name based on verifier result and retry guard."""
    if state.get("_verifier_passed", True):
        return "formatter"
    return "question_planner"


# ──────────────────────────────────────────────────────────────────────────────
# Graph construction
# ──────────────────────────────────────────────────────────────────────────────

workflow = StateGraph(GraphState)

workflow.add_node("analyzer", node_analyzer)
workflow.add_node("text_cleaner", node_text_cleaner)
workflow.add_node("question_planner", node_question_planner)
workflow.add_node("verifier", node_verifier)
workflow.add_node("formatter", node_formatter)

workflow.add_edge(START, "analyzer")
workflow.add_edge("analyzer", "text_cleaner")
workflow.add_edge("text_cleaner", "question_planner")
workflow.add_edge("question_planner", "verifier")
workflow.add_conditional_edges(
    "verifier",
    route_after_verifier,
    {
        "question_planner": "question_planner",
        "formatter": "formatter",
    },
)
workflow.add_edge("formatter", END)

app = workflow.compile()
