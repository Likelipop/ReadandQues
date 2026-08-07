import json
from pathlib import Path
from typing import Any, Dict, List

from service.ai_core.utils.config import ExamConfig


def _read_prompt(filename: str) -> str:
    return (Path(__file__).parent / filename).read_text(encoding="utf-8")


def build_analysis_prompt(text: str) -> str:
    template = _read_prompt("analyzer.md")
    return template.format(text=text)


def _format_analysis_context(analysis: Dict[str, Any]) -> str:
    """Serialize the most exam-relevant parts of SemanticAnalysis for prompt injection."""
    core = analysis.get("core", {})
    lines = [
        f"Genre: {analysis.get('genre', 'general')}",
        f"Summary: {core.get('summary', '')}",
        f"Central Theme: {core.get('central_theme', '')}",
        f"Tone: {core.get('tone', '')}",
    ]
    if core.get("ambiguities"):
        lines.append(
            "Ambiguities (use for Not Given traps):\n  - "
            + "\n  - ".join(core["ambiguities"])
        )
    if core.get("likely_misunderstood"):
        lines.append(
            "Likely Misunderstood:\n  - " + "\n  - ".join(core["likely_misunderstood"])
        )
    if core.get("key_terms"):
        lines.append("Key Terms: " + json.dumps(core["key_terms"], ensure_ascii=False))

    for genre_key in ("narrative", "poetry", "scientific", "persuasive"):
        genre_data = analysis.get(genre_key)
        if genre_data:
            lines.append(
                f"\n[{genre_key.upper()} ANALYSIS]\n"
                + json.dumps(genre_data, ensure_ascii=False, indent=2)
            )
            break
    return "\n".join(lines)


def build_question_prompt(
    text: str,
    analysis: Dict[str, Any],
    config: ExamConfig,
) -> str:
    analysis_context = _format_analysis_context(analysis)

    total = config.total_questions
    if total <= 7:
        ynng_count = total - 3
        fib_count = 1
        mcq_count = 2
    elif total <= 10:
        ynng_count = total - 4
        fib_count = 1
        mcq_count = 3
    else:
        ynng_count = total - 5
        fib_count = 1
        mcq_count = 4

    template = _read_prompt("question_planner.md")
    return template.format(
        analysis_context=analysis_context,
        word_count=config.word_count,
        text=text,
        total=total,
        ynng_count=ynng_count,
        fib_count=fib_count,
        mcq_count=mcq_count,
    )


def build_verifier_prompt(text: str, quizzes: List[Dict[str, Any]]) -> str:
    quizzes_json = json.dumps(quizzes, ensure_ascii=False, indent=2)
    template = _read_prompt("verifier.md")
    return template.format(text=text, quizzes_json=quizzes_json)
