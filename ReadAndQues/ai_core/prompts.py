"""
ai_core/prompts.py — Modular prompt builders for the 4-node LangGraph pipeline.

Public API:
    build_analysis_prompt(text)                      → str  (Node 1: analyzer)
    build_question_prompt(text, analysis, config)    → str  (Node 2: question_planner)
    build_verifier_prompt(text, quizzes)             → str  (Node 3: verifier)
"""

import json
from typing import Any, Dict, List

from .config import ExamConfig


# ============================================================
# NODE 1 — ANALYZER PROMPT
# ============================================================

def build_analysis_prompt(text: str) -> str:
    return f"""You are a world-class literary scholar and reading specialist.

Your task is to perform a deep semantic analysis of the article below.

STEP 1 — CLASSIFY the genre. Choose exactly one:
  • "narrative"   — fiction, novel excerpt, short story, drama
  • "poetry"      — poem, lyric
  • "scientific"  — research paper, academic or scientific article
  • "persuasive"  — opinion piece, editorial, news analysis, argumentative essay
  • "general"     — anything that does not fit the above

STEP 2 — Fill in `core` (applies to ALL genres). Be specific and grounded in the text.

STEP 3 — Fill in the genre-specific sub-analysis that matches your genre classification.
  Leave all other genre sub-fields as null.
  If genre = "general", all genre-specific fields may be null.

CRITICAL RULES:
• `key_terms` must be a dict mapping term → concise definition (max 2 sentences).
• `ambiguities` should list passages/claims that could be read multiple ways — these
  are gold for generating challenging "Not Given" or "evaluate" type questions.
• `likely_misunderstood` should list traps that test surface readers.
• Be precise. Do NOT pad with vague filler text.

=== ARTICLE ===
{text}
"""


# ============================================================
# NODE 2 — QUESTION PLANNER PROMPT
# ============================================================

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
        lines.append("Ambiguities (use for Not Given traps):\n  - " + "\n  - ".join(core["ambiguities"]))
    if core.get("likely_misunderstood"):
        lines.append("Likely Misunderstood:\n  - " + "\n  - ".join(core["likely_misunderstood"]))
    if core.get("key_terms"):
        lines.append("Key Terms: " + json.dumps(core["key_terms"], ensure_ascii=False))

    # Append genre-specific context
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

    # Question count allocation
    total = config.total_questions
    # Distribution: ~50% YNNG, ~30% FIB (1 task = 5 blanks), ~20% MCQ
    # But FIB is always exactly 1 task worth 5 sub-answers → counts as 1 quiz item
    if total <= 7:
        ynng_count = total - 2
        fib_count  = 1      # 1 summary completion task (worth 5 blanks)
        mcq_count  = 1
    elif total <= 10:
        ynng_count = total - 3
        fib_count  = 1
        mcq_count  = 2
    else:  # 14+
        ynng_count = total - 4
        fib_count  = 1
        mcq_count  = 3

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
  - Yes       → statement AGREES with the writer's explicit/strongly implied claim
  - No        → statement CONTRADICTS the writer's claim
  - Not Given → topic appears in the text but the OVERALL CLAIM cannot be confirmed
                ← use the pre-computed ambiguities to craft tricky Not Given items

RULES:
1. Each statement is a DECLARATIVE sentence about the WRITER'S VIEWS, not facts in general.
2. Statements must be PARAPHRASED — never copy verbatim.
3. supporting_text: verbatim sentence(s) from the article that justify the answer.
4. explanation: explain precisely WHY the answer is Yes / No / Not Given.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TYPE B — SUMMARY COMPLETION / FILL IN THE BLANK  ({fib_count} task)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
quiz_type: "fill_in_blank"
question: A cohesive summary paragraph (70–130 words) covering key points,
          containing exactly 5 blanks written as [1], [2], [3], [4], [5].
options: null
correct_answer: answers separated by " | "
  Example: "climate change | fossil fuels | carbon dioxide | renewable energy | net zero"
CRITICAL: every blank answer MUST be a word / short phrase (≤ 3 words) taken VERBATIM
          from the article. Do NOT paraphrase blank answers.
explanation: for each blank, quote the source sentence and explain the fit.
supporting_text: verbatim sentence(s) where all 5 answers are found.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TYPE C — MULTIPLE CHOICE  ({mcq_count} questions)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
quiz_type: "multiple_choice"
options: exactly 4 options (A, B, C, D format: "A. ...", "B. ...", etc.)
correct_answer: the full text of the correct option, e.g. "A. ..."

PARAPHRASE RULES (CRITICAL — enforced by verifier):
• The question stem MUST be PARAPHRASED — do NOT copy any sentence verbatim.
• ALL 4 options MUST be PARAPHRASED — none should copy the article word-for-word.
• The answer must still be provably correct via `supporting_text` (verbatim from article).
• This means: rephrase the question and options, but the underlying fact stays grounded.

CONTENT RULES:
1. Test inference, vocabulary in context, or author purpose — NOT simple recall.
2. Distractors must be plausible (partially true or related to the text) — no obviously wrong options.
3. supporting_text: verbatim sentence(s) from the article justifying the correct answer.
4. explanation: explain why the correct option is right AND briefly why each distractor is wrong.


GLOBAL RULES (all types):
• Use sophisticated academic vocabulary.
• Do NOT create trivially obvious questions.
• Each question must be uniquely grounded in a DIFFERENT part of the article.
"""


# ============================================================
# NODE 3 — VERIFIER PROMPT
# ============================================================

def build_verifier_prompt(text: str, quizzes: List[Dict[str, Any]]) -> str:
    quizzes_json = json.dumps(quizzes, ensure_ascii=False, indent=2)
    return f"""You are a strict IELTS exam quality-control reviewer.

Your job: verify that each quiz question is properly grounded in the article.

=== ARTICLE ===
{text}

=== QUESTIONS TO VERIFY (JSON) ===
{quizzes_json}

=== VERIFICATION CHECKLIST (check ALL of these per question) ===
For each question at index i (0-based):
  1. Does `supporting_text` appear VERBATIM (or near-verbatim) in the article?
  2. Does `correct_answer` logically follow from `supporting_text`?
  3. For fill_in_blank: does each blank answer appear VERBATIM in the article?
  4. For yes_no_notgiven: is the classification accurate (not a Yes disguised as Not Given)?
  5. For multiple_choice: are all 4 options present? Is exactly one correct?

=== OUTPUT FORMAT ===
Return:
  passed: true  — if ALL questions pass ALL checks
  passed: false — if ANY question fails
  rejected_indices: list of 0-based indices that failed (empty if passed)
  reason: brief explanation of each failure (one sentence per failed question)

Be STRICT. If a supporting_text cannot be found in the article, reject the question.
Do NOT accept paraphrased supporting_text — it must be verbatim or very close.
"""
