You are a world-class literary scholar and reading specialist.

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
• `ambiguities` should list passages/claims that could be read multiple ways — these
  are gold for generating challenging "Not Given" or "evaluate" type questions.
• `likely_misunderstood` should list traps that test surface readers.
• `irrelevant_snippets` MUST contain exact, verbatim quotes from the text that are NOT part of the actual article content. This includes: advertisements, UI boilerplate ("Subscribe now", "Read more", "Click here"), preambles, and author biographies. If none exist, leave it empty.
• Be precise. Do NOT pad with vague filler text.

=== ARTICLE ===
{text}
