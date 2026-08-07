import logging
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langchain_core.output_parsers import JsonOutputParser
from service.ai_core.connection.router import get_llm
from .schemas import SmartParaphraseState, SmartParaphraseOutput, ValidatorOutput
from .prompts import get_generator_prompt, get_validator_prompt

logger = logging.getLogger(__name__)


def generator_node(state: SmartParaphraseState) -> Dict[str, Any]:
    logger.info(f"Generator Node: attempt {state['retry_count'] + 1}")
    llm = get_llm(temperature=1.0)
    parser = JsonOutputParser(pydantic_object=SmartParaphraseOutput)

    prompt = get_generator_prompt()
    prompt = prompt.partial(format_instructions=parser.get_format_instructions())

    feedback_str = ""
    if state.get("validation_feedback") and state["retry_count"] > 0:
        feedback_str = f"\nWARNING from Previous Attempt: {state['validation_feedback']}\nPlease fix these issues!\n"

    chain = prompt | llm | parser

    try:
        result = chain.invoke({
            "highlighted_text": state["highlighted_text"],
            "paragraph_context": state["paragraph_context"],
            "validation_feedback": feedback_str
        })
        return {
            "expanded_text": result.get("expanded_text", state["highlighted_text"]),
            "paraphrased_text": result.get("paraphrased_text", state["highlighted_text"]),
            "explanation": result.get("explanation", ""),
            "retry_count": state["retry_count"] + 1
        }
    except Exception as e:
        logger.error(f"Error in smart paraphrase generator: {e}")
        return {
            "expanded_text": state["highlighted_text"],
            "paraphrased_text": state["highlighted_text"],
            "explanation": "Error during generation.",
            "retry_count": state["retry_count"] + 1
        }


def validator_node(state: SmartParaphraseState) -> Dict[str, Any]:
    logger.info("Validator Node: checking paraphrase accuracy")
    llm = get_llm(temperature=0.1)
    parser = JsonOutputParser(pydantic_object=ValidatorOutput)

    prompt = get_validator_prompt()
    prompt = prompt.partial(format_instructions=parser.get_format_instructions())

    chain = prompt | llm | parser
    try:
        result = chain.invoke({
            "expanded_text": state["expanded_text"],
            "paraphrased_text": state["paraphrased_text"]
        })
        is_valid = result.get("is_valid", False)
        feedback = result.get("feedback", "")
        if not is_valid:
            logger.warning(f"Validation failed: {feedback}")
        else:
            logger.info("Validation passed!")

        return {
            "is_valid": is_valid,
            "validation_feedback": feedback
        }
    except Exception as e:
        logger.error(f"Error in validator: {e}")
        return {
            "is_valid": True,
            "validation_feedback": "Validator failed to parse."
        }


def should_continue(state: SmartParaphraseState) -> str:
    if state["is_valid"]:
        return "end"
    if state["retry_count"] >= 3:
        logger.warning("Max retries reached. Forcing end.")
        return "end"
    return "generate"


workflow = StateGraph(SmartParaphraseState)
workflow.add_node("generator", generator_node)
workflow.add_node("validator", validator_node)

workflow.set_entry_point("generator")
workflow.add_edge("generator", "validator")
workflow.add_conditional_edges(
    "validator",
    should_continue,
    {
        "end": END,
        "generate": "generator"
    }
)

app = workflow.compile()


def run_smart_paraphrase_flow(highlighted_text: str, 
                              paragraph_text: str, 
                              start_idx: int = 0, 
                              end_idx: int = 0) -> dict:
    initial_state = {
        "highlighted_text": highlighted_text,
        "paragraph_context": paragraph_text,
        "expanded_text": "",
        "paraphrased_text": "",
        "explanation": "",
        "is_valid": False,
        "validation_feedback": "",
        "retry_count": 0,
    }
    return app.invoke(initial_state)


def run_smart_paraphrase_llm(highlighted_text: str, paragraph_text: str) -> dict:
    return run_smart_paraphrase_flow(highlighted_text, paragraph_text)
