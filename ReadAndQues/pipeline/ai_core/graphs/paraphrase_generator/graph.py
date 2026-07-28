import logging
from typing import Any, Dict, TypedDict

from langgraph.graph import END, START, StateGraph

from pipeline.ai_core.connection import get_llm
from pipeline.ai_core.graphs.paraphrase_generator.prompts import build_paraphrase_prompt
from pipeline.ai_core.graphs.paraphrase_generator.schemas import ParaphraseOutput

logger = logging.getLogger(__name__)


class ParaphraseState(TypedDict):
    text: str
    phrases: list[dict]


def generate_paraphrase_node(state: ParaphraseState) -> Dict[str, Any]:
    text = state["text"]
    llm = get_llm(temperature=0.7)
    prompt = build_paraphrase_prompt()
    chain = prompt | llm.with_structured_output(ParaphraseOutput)
    
    try:
        result = chain.invoke({"text": text})
        # Convert to dictionary format
        phrases = [
            {
                "original_text": p.original_text,
                "alternatives": p.alternatives
            }
            for p in result.phrases
        ]
        return {"phrases": phrases}
    except Exception as e:
        logger.error(f"Error in generate_paraphrase node: {e}")
        return {"phrases": []}


builder = StateGraph(ParaphraseState)
builder.add_node("generate", generate_paraphrase_node)
builder.add_edge(START, "generate")
builder.add_edge("generate", END)

app = builder.compile()
