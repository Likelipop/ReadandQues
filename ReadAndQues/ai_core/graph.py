"""Single-call IELTS exam generator graph."""

import uuid
from typing import Any, Dict, List, Optional

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from .config import ExamConfig, get_llm
from .prompts import build_prompt
from .schemas import ExamOutput, GraphState, QuizItem


def _log_token_usage(raw_message: Any) -> None:
    usage = getattr(raw_message, "usage_metadata", None) or {}
    input_tok = usage.get("input_tokens", "N/A")
    output_tok = usage.get("output_tokens", "N/A")
    print(f"📊 Token Usage — Input: {input_tok} | Output: {output_tok}")


def node_generator(state: GraphState) -> Dict[str, Any]:
    text = state["original_text"]
    config = ExamConfig.from_text(text)
    prompt = build_prompt(text, config)

    llm = get_llm()
    structured_llm = llm.with_structured_output(ExamOutput, include_raw=True)
    raw_result = structured_llm.invoke(prompt)

    parsed: ExamOutput = raw_result["parsed"]
    _log_token_usage(raw_result["raw"])

    return {
        "exam_config": config.model_dump(),
        "final_exam": {
            "exam_id": f"EXAM_{uuid.uuid4().hex[:12].upper()}",
            "total_questions": len(parsed.quizzes),
            "quizzes": [q.model_dump() for q in parsed.quizzes],
        },
    }


workflow = StateGraph(GraphState)
workflow.add_node("generator", node_generator)
workflow.add_edge(START, "generator")
workflow.add_edge("generator", END)

app = workflow.compile()