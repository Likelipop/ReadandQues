"""
ReadAndQues/AI_core/prompts.py — Prompt builders for IELTS exam generation.
"""

import json
from typing import Any, Dict, List
from .config import ExamConfig


def build_analysis_prompt(text: str) -> str:
    return f"""You are a world-class literary scholar and reading specialist.

Your task is to perform a deep semantic analysis of the article below.

STEP 1 — CLASSIFY the genre and theme:
Genre (choose exactly one):
  • "narrative"   — fiction, novel excerpt, short story, drama
  • "poetry"      — poem, lyric
  • "scientific"  — research paper, academic or scientific article
  • "persuasive"  — opinion piece, editorial, news analysis, argumentative essay
  • "general"     — anything that does not fit the above

Theme (choose exactly one primary category):
  • "Economy"     — economics, trade, business, finance, markets
  • "Society"     — sociology, human affairs, social issues, community
  • "Education"   — schooling, teaching, learning, literacy, academic study
  • "Technology"  — computer science, AI, engineering, digital innovation
  • "Science"     — physics, biology, astronomy, natural sciences, research
  • "Environment" — climate change, ecology, conservation, natural habitats
  • "Culture"     — history, art, music, literature, heritage
  • "Health"      — medicine, healthcare, wellness, psychology
  • "General"     — miscellaneous or multi-domain topics

STEP 2 — Fill in `core` (applies to ALL genres). Be specific and grounded in the text.

STEP 3 — Fill in the genre-specific sub-analysis that matches your genre classification.
  Leave all other genre sub-fields as null.
  If genre = "general", all genre-specific fields may be null.

CRITICAL RULES:
• `key_terms` must be a dict mapping term → concise definition (max 2 sentences).
• `ambiguities` should list passages/claims that could be read multiple ways.
• `likely_misunderstood` should list traps that test surface readers.
• `irrelevant_snippets` MUST contain exact, verbatim quotes from the text that are NOT part of the actual article content.
• Be precise. Do NOT pad with vague filler text.

=== ARTICLE ===
{text}
"""


def _format_analysis_context(analysis: Dict[str, Any]) -> str:
    core = analysis.get("core", {})
    lines = [
        f"Genre: {analysis.get('genre', 'general')}",
        f"Summary: {core.get('summary', '')}",
        f"Central Theme: {core.get('central_theme', '')}",
        f"Tone: {core.get('tone', '')}",
    ]
    if core.get("ambiguities"):
        lines.append("Ambiguities (use for Not Given traps):\n  - " + "\n  - ".join(core["ambiguities"]))
    if core.get("likely_misunderstood"):
        lines.append("Likely Misunderstood:\n  - " + "\n  - ".join(core["likely_misunderstood"]))
    if core.get("key_terms"):
        lines.append("Key Terms: " + json.dumps(core["key_terms"], ensure_ascii=False))

    for genre_key in ("narrative", "poetry", "scientific", "persuasive"):
        genre_data = analysis.get(genre_key)
        if genre_data:
            lines.append(f"\n[{genre_key.upper()} ANALYSIS]\n" + json.dumps(genre_data, ensure_ascii=False, indent=2))
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
        fib_count  = 1
        mcq_count  = 2
    elif total <= 10:
        ynng_count = total - 4
        fib_count  = 1
        mcq_count  = 3
    else:
        ynng_count = total - 5
        fib_count  = 1
        mcq_count  = 4

    return f"""You are a world-class IELTS Exam Architect.

=== SEMANTIC ANALYSIS (pre-computed — use to ground your questions) ===
{analysis_context}

=== ARTICLE ({config.word_count} words) ===
{text}

=== YOUR TASK ===
Generate exactly {total} IELTS Academic Reading questions in this breakdown:
  • {ynng_count} × Yes / No / Not Given
  • {fib_count}  × Summary Completion (Fill in the Blank)
  • {mcq_count}  × Multiple Choice

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TYPE A — YES / NO / NOT GIVEN  ({ynng_count} questions)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
quiz_type: "yes_no_notgiven"
options: always ["Yes", "No", "Not Given"]
correct_answer: exactly "Yes", "No", or "Not Given"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TYPE B — SUMMARY COMPLETION / FILL IN THE BLANK  ({fib_count} task)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
quiz_type: "fill_in_blank"
question: A cohesive summary paragraph (70–130 words) covering key points,
          containing exactly 5 blanks written as [1], [2], [3], [4], [5].
options: null
correct_answer: answers separated by " | "

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TYPE C — MULTIPLE CHOICE  ({mcq_count} questions)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
quiz_type: "multiple_choice"
options: exactly 4 options (A, B, C, D format: "A. ...", "B. ...", etc.)
correct_answer: the full text of the correct option, e.g. "A. ..."

GLOBAL RULES:
• Use sophisticated academic vocabulary.
• Do NOT create trivially obvious questions.
• Each question must be uniquely grounded in a DIFFERENT part of the article.
"""


def build_verifier_prompt(text: str, quizzes: List[Dict[str, Any]]) -> str:
    quizzes_json = json.dumps(quizzes, ensure_ascii=False, indent=2)
    return f"""You are a strict IELTS exam quality-control reviewer.

Your job: verify that each quiz question is properly grounded in the article.

=== ARTICLE ===
{text}

=== QUESTIONS TO VERIFY (JSON) ===
{quizzes_json}

=== OUTPUT FORMAT ===
Return:
  passed: true  — if ALL questions pass ALL checks
  passed: false — if ANY question fails
  rejected_indices: list of 0-based indices that failed
  reason: brief explanation of each failure
"""
