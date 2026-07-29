import logging
from typing import Dict
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pipeline.ai_core.connection.router import get_llm
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class SmartParaphraseOutput(BaseModel):
    expanded_text: str = Field(description="The expanded highlighted text to ensure complete meaning.")
    paraphrased_text: str = Field(description="The simplified or annotated version of the expanded text.")


def run_smart_paraphrase_llm(highlighted_text: str, paragraph_context: str) -> Dict[str, str]:
    """
    Invokes the LLM to process a highlighted text within its paragraph context.
    Returns a dictionary with 'expanded_text' and 'paraphrased_text'.
    """
    llm = get_llm(temperature=1.0)
    parser = JsonOutputParser(pydantic_object=SmartParaphraseOutput)

    prompt = PromptTemplate(
        template="""You are an expert English teacher. The user is reading a paragraph and has highlighted a specific text snippet because they find it difficult to understand.

Your task is to help them understand it by following these steps:
1. **Expand if necessary**: Look at the <highlighted_text>. If it is cut off or incomplete (e.g., missing a verb or subject), expand it using the <paragraph_context> so that it forms a complete, coherent phrase or clause. If it is already complete, keep it as is. This will be your `expanded_text`. The `expanded_text` MUST be an exact substring of the <paragraph_context>.
2. **Analyze and Paraphrase**: Analyze the `expanded_text` within the context.
   - If the grammar/structure is complex: Rewrite it using simpler, clearer grammar. CRITICAL: Do NOT change or lose the original meaning.
   - If the vocabulary is difficult: Replace it with a more common synonym.
   - If it contains a specialized terminology (e.g., scientific, medical, business jargon): Do NOT replace the term. Instead, append a short definition next to it in this format: `term - (definition)`. Example: `photosynthesis - (the process by which plants make their own food)`.

<paragraph_context>
{paragraph_context}
</paragraph_context>

<highlighted_text>
{highlighted_text}
</highlighted_text>

{format_instructions}
""",
        input_variables=["highlighted_text", "paragraph_context"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )

    chain = prompt | llm | parser

    try:
        result = chain.invoke({
            "highlighted_text": highlighted_text,
            "paragraph_context": paragraph_context
        })
        return {
            "expanded_text": result.get("expanded_text", highlighted_text),
            "paraphrased_text": result.get("paraphrased_text", highlighted_text)
        }
    except Exception as e:
        logger.error(f"Error in smart paraphrase LLM: {e}")
        return {
            "expanded_text": highlighted_text,
            "paraphrased_text": highlighted_text
        }
