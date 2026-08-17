import json
from pathlib import Path
from typing import Any, Dict, List

from service.ai_core.utils.config import ExamConfig


def _read_prompt(filename: str) -> str:
    return (Path(__file__).parent / filename).read_text(encoding="utf-8")


def build_analysis_prompt(text: str) -> str:
    template = _read_prompt("analyzer.md")
    return template.format(text=text)


def _format_analysis_context(analysis: dict[str, Any]) -> str:
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
    analysis: dict[str, Any],
    config: ExamConfig,
) -> str:
    analysis_context = _format_analysis_context(analysis)

    total = config.total_questions

    # Dynamic scaling based on total requested
    if total <= 3:
        ynng_count = 3
        fib_count = 0
        mcq_count = 0
    elif total <= 5:
        ynng_count = 3
        fib_count = 0
        mcq_count = 2
    elif total <= 7:
        ynng_count = 4
        fib_count = 1
        mcq_count = 2
    elif total <= 10:
        ynng_count = 4
        fib_count = 1
        mcq_count = 3
    else:
        ynng_count = 5
        fib_count = 1
        mcq_count = 4

    # Build Breakdown List
    breakdown_list = []
    if ynng_count > 0:
        breakdown_list.append(f"  • {ynng_count} × Yes / No / Not Given")
    if fib_count > 0:
        breakdown_list.append(f"  • {fib_count}  × Summary Completion (Fill in the Blank)")
    if mcq_count > 0:
        breakdown_list.append(f"  • {mcq_count}  × Multiple Choice")

    breakdown_str = "\n".join(breakdown_list)

    # Build Quiz Type Instructions
    instructions = []
    if ynng_count > 0:
        instructions.append(f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TYPE A — YES / NO / NOT GIVEN  ({ynng_count} questions)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
quiz_type: "yes_no_notgiven"
options: always ["Yes", "No", "Not Given"]
correct_answer: exactly "Yes", "No", or "Not Given"
""")

    if fib_count > 0:
        instructions.append(f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TYPE B — SUMMARY COMPLETION / FILL IN THE BLANK  ({fib_count} task)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
quiz_type: "fill_in_blank"
question: A cohesive summary paragraph (70–130 words) covering key points, choice exactly those with no longer than three words, and easy to be mis-understanding, that word/phrase must be appear in the text.. 
          containing exactly 5 blanks written as [1], [2], [3], [4], [5],
          .
options: null
correct_answer: answers separated by " | "
""")

    if mcq_count > 0:
        instructions.append(f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TYPE C — MULTIPLE CHOICE  ({mcq_count} questions)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
quiz_type: "multiple_choice"
options: exactly 4 options (A, B, C, D format: "A. ...", "B. ...", etc.)
correct_answer: the full text of the correct option, e.g. "A. ..."
""")

    instructions_str = "\n".join(instructions)

    template = _read_prompt("question_planner.md")
    return template.format(
        analysis_context=analysis_context,
        word_count=config.word_count,
        text=text,
        total=total,
        breakdown_list=breakdown_str,
        quiz_type_instructions=instructions_str,
    )


def build_verifier_prompt(text: str, quizzes: list[dict[str, Any]]) -> str:
    quizzes_json = json.dumps(quizzes, ensure_ascii=False, indent=2)
    template = _read_prompt("verifier.md")
    return template.format(text=text, quizzes_json=quizzes_json)
