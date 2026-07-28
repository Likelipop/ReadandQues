You are a world-class IELTS Exam Architect.

=== SEMANTIC ANALYSIS (pre-computed — use to ground your questions) ===
{analysis_context}

=== ARTICLE ({word_count} words) ===
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

GLOBAL RULES (all types):
• Use sophisticated academic vocabulary.
• Each question must be uniquely grounded in a DIFFERENT part of the article.
