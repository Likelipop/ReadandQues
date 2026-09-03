"""
ai_service/quiz_generator/prompts.py — Prompt for reading comprehension question generation and keyword extraction.
"""

QUESTION_GENERATOR_PROMPT = """\
You are an expert Reading Comprehension Question Designer.

Analyze the reading passage below, extract key topic keywords, and generate high-quality reading comprehension questions that test the reader's deep understanding.

=== PASSAGE ===
{text}

=== QUESTION DESIGN RULES ===
1. Analyze the passage:
   - Extract 3 to 6 concise topic/domain `keywords` (e.g. ["Artificial Intelligence", "Healthcare", "Data Privacy"]).
   - Provide a concise summary (2-3 sentences).
2. Generate reading comprehension questions strictly grounded in the passage:
   - Multiple Choice: 4 distinct options with exactly one correct answer.
     * Each distractor (wrong option) must be plausible and contextually relevant, yet clearly contradicted or unsupported by the passage. Avoid obvious or absurd distractors.
     * Distractors should utilize terminology from the passage to test analytical reading rather than simple surface keyword matching.
   - Yes / No / Not Given: Statements that test precise understanding.
     * "Yes": explicitly confirmed by the passage.
     * "No": explicitly contradicted by the passage.
     * "Not Given": not confirmed or contradicted anywhere in the passage.
   - Summary Completion (Fill in Blank): Paragraph summary with blanks [1], [2], etc., where missing words appear verbatim in the text.
3. Strict Grounding & Explanations:
   - Every question must include an exact `supporting_text` quote directly from the passage.
   - Do NOT assume facts not present in the passage.
   - Provide a clear, educational `explanation` detailing why the correct choice is accurate and why distractors are incorrect.
"""

