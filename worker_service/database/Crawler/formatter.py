"""
worker_service/database/Crawler/formatter.py — Text formatting utilities.
"""


def to_markdown(text: str) -> str:
    """
    Format raw article text into Markdown format:
    1. Splits paragraphs by newline ('\n').
    2. Automatically adds bullet points ('- ') to subsequent paragraphs after a line ending with ':'
       if the paragraph has less than 13 words AND no more than 2 sentences separated by '.'.
    3. Formats paragraphs with double newlines ('\n\n') to double the spacing between paragraphs for readability.
    """
    if not text:
        return ""

    raw_lines = text.split("\n")
    formatted_paragraphs = []
    in_bullet_mode = False

    for line in raw_lines:
        cleaned = line.strip()
        if not cleaned:
            continue

        if in_bullet_mode:
            words = cleaned.split()
            word_count = len(words)
            sentences = [s for s in cleaned.split(".") if s.strip()]
            sentence_count = len(sentences)

            if word_count < 13 and sentence_count <= 2:
                if not cleaned.startswith(("-", "*", "+", "•")):
                    cleaned = f"- {cleaned}"
                formatted_paragraphs.append(cleaned)
                if cleaned.endswith(":"):
                    in_bullet_mode = True
                continue
            else:
                in_bullet_mode = False

        formatted_paragraphs.append(cleaned)
        if cleaned.endswith(":"):
            in_bullet_mode = True

    if not formatted_paragraphs:
        return ""

    # Smart join: adjacent list items separated by '\n', separate paragraphs by '\n\n' (double spacing)
    result_lines = []
    for i, line in enumerate(formatted_paragraphs):
        if i == 0:
            result_lines.append(line)
        else:
            prev_line = formatted_paragraphs[i - 1]
            if line.startswith("- ") and (
                prev_line.startswith("- ") or prev_line.endswith(":")
            ):
                result_lines.append("\n" + line)
            else:
                result_lines.append("\n\n" + line)

    return "".join(result_lines)
