"""
Modular prompt block system.

Each block is a function: (article_text, config) -> str.
ACTIVE_BLOCKS controls which blocks compose the megaprompt.
build_prompt() joins all active blocks into one string.

To add a new question type:
  1. Define a block_xxx(article_text, config) function.
  2. Append it to ACTIVE_BLOCKS.
"""

from typing import Callable, List

from .config import ExamConfig

PromptBlock = Callable[[str, ExamConfig], str]


def block_system_role(article_text: str, config: ExamConfig) -> str:
    return (
        "You are a world-class IELTS Exam Architect and a native "
        "English-speaking reading specialist.\n\n"
        "=== YOUR TASK ===\n"
        "Read the article below. Perform deep native-level comprehension "
        "internally (do NOT output your analysis).\n"
        f"Then generate exactly {config.total_questions} IELTS Academic "
        "Reading questions following the type-specific rules below."
    )


def block_article(article_text: str, config: ExamConfig) -> str:
    return f"=== ARTICLE ({config.word_count} words) ===\n{article_text}"


def block_deep_analysis(article_text: str, config: ExamConfig) -> str:
    return (
        "=== INTERNAL ANALYSIS (perform silently, do NOT include in output) ===\n"
        "1. Identify the MAIN THESIS: What is the author's core argument or finding?\n"
        "2. Map AUTHOR'S TONE: objective, critical, optimistic, alarmed, ironic?\n"
        "3. Detect IMPLICIT CONTRASTS & SUBTLETIES: tensions, ironies, unstated assumptions\n"
        "4. Identify KEY CLAIMS, EVIDENCE, and CONCLUSIONS across the article"
    )


def block_yes_no_notgiven(article_text: str, config: ExamConfig) -> str:
    yn_count = config.total_questions - 5
    return (
        "=== QUESTION TYPE A: YES / NO / NOT GIVEN ===\n"
        f"Generate exactly {yn_count} Yes/No/Not Given statements.\n\n"
        "RULES:\n"
        '1. quiz_type: "yes_no_notgiven"\n'
        "2. Each statement is a DECLARATIVE sentence testing the WRITER'S VIEWS or CLAIMS.\n"
        '3. options: always ["Yes", "No", "Not Given"]\n'
        '4. correct_answer: exactly one of "Yes", "No", or "Not Given"\n'
        "   - Yes       → Agrees with the writer's explicit or strongly implied claim.\n"
        "   - No        → Contradicts the writer's claim.\n"
        "   - Not Given → The text may container some that have in the text but the overall is no exactly in the test use this when you see that it is likely to trap the reader, using your understanding to trap.\n"
        "5. Statements must be PARAPHRASED — never copy verbatim from the text.\n"
        "6. Use sophisticated vocabulary; test inference, author_purpose, vocabulary_in_context.\n"
        "7. supporting_text: exact verbatim sentence(s) from the article justifying the answer.\n"
        "8. explanation: explain WHY the answer is Yes/No/Not Given."
    )


def block_summary_completion(article_text: str, config: ExamConfig) -> str:
    return (
        "=== QUESTION TYPE B: SUMMARY COMPLETION (FILL IN THE BLANK) ===\n"
        "Generate exactly 1 Summary Completion task (worth 5 questions).\n\n"
        "RULES:\n"
        '1. quiz_type: "fill_in_blank"\n'
        "2. Write a cohesive summary paragraph (70-130 words) covering the article's key points.\n"
        "3. The paragraph must contain exactly 5 blanks: [1], [2], [3], [4], [5].\n"
        "4. CRITICAL: Each blank answer MUST be a word or short phrase (≤2 words) "
        "taken VERBATIM from the article.\n"
        "5. question: The summary paragraph with [1]...[5] inline.\n"
        "6. options: null\n"
        '7. correct_answer: answers separated by " | "\n'
        '   Example: "climate change | fossil fuels | carbon dioxide | renewable energy | net zero"\n'
        "8. explanation: For each blank, quote the source sentence and explain why that word fits.\n"
        "9. supporting_text: The verbatim sentence(s) where each answer is found."
    )


ACTIVE_BLOCKS: List[PromptBlock] = [
    block_system_role,
    block_article,
    block_deep_analysis,
    block_yes_no_notgiven,
    block_summary_completion,
]


def build_prompt(article_text: str, config: ExamConfig) -> str:
    return "\n\n".join(block(article_text, config) for block in ACTIVE_BLOCKS)
