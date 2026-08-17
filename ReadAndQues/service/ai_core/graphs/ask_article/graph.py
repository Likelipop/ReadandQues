import logging
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from service.ai_core.connection import get_llm
from service.ai_core.grounding import chunk_article_text, retrieve_article_chunks

logger = logging.getLogger(__name__)


class GroundedAnswerSchema(BaseModel):
    has_evidence: bool
    answer: str
    citation_quote: str | None = ""
    chunk_id: str | None = ""


class AskArticleState(TypedDict):
    article_text: str
    question: str
    chunks: list[dict[str, Any]]
    retrieved_chunks: list[dict[str, Any]]
    answer: str
    citation_quote: str
    chunk_id: str
    is_grounded: bool


def node_chunk_and_retrieve(state: AskArticleState) -> dict[str, Any]:
    article_text = state["article_text"]
    question = state["question"]

    chunks = chunk_article_text(article_text)
    retrieved = retrieve_article_chunks(chunks, question, top_k=3)

    return {
        "chunks": [c.model_dump() for c in chunks],
        "retrieved_chunks": [c.model_dump() for c in retrieved],
    }


def node_generate_grounded_answer(state: AskArticleState) -> dict[str, Any]:
    retrieved = state.get("retrieved_chunks", [])
    question = state["question"]

    if not retrieved:
        return {
            "answer": "not_found_in_article",
            "citation_quote": "",
            "chunk_id": "",
            "is_grounded": False,
        }

    context_str = "\n\n".join(f"[{c['chunk_id']}] {c['text']}" for c in retrieved)
    prompt = (
        f"You are a strict grounded Q&A assistant. Answer the question using ONLY the article excerpts provided below.\n"
        f"If the answer cannot be found directly in the excerpts, set has_evidence=False and answer='not_found_in_article'.\n"
        f"If evidence exists, set has_evidence=True, provide a direct answer, and include the exact quote from the chunk.\n\n"
        f"Excerpts:\n{context_str}\n\n"
        f"Question: {question}"
    )

    try:
        llm = get_llm(temperature=0.0)
        structured_llm = llm.with_structured_output(GroundedAnswerSchema)
        result: GroundedAnswerSchema = structured_llm.invoke(prompt)

        if not result.has_evidence or result.answer == "not_found_in_article":
            return {
                "answer": "not_found_in_article",
                "citation_quote": "",
                "chunk_id": "",
                "is_grounded": False,
            }

        return {
            "answer": result.answer,
            "citation_quote": result.citation_quote or "",
            "chunk_id": result.chunk_id or (retrieved[0]["chunk_id"] if retrieved else ""),
            "is_grounded": True,
        }
    except Exception as e:
        logger.error(f"Error generating grounded answer: {e}")
        return {
            "answer": "not_found_in_article",
            "citation_quote": "",
            "chunk_id": "",
            "is_grounded": False,
        }


def node_verify_grounding(state: AskArticleState) -> dict[str, Any]:
    answer = state.get("answer", "")
    quote = state.get("citation_quote", "")
    retrieved = state.get("retrieved_chunks", [])

    if answer == "not_found_in_article" or not state.get("is_grounded", False):
        return {"answer": "not_found_in_article", "is_grounded": False}

    if not quote or not quote.strip():
        # Citation quote required for verification
        return {"answer": "not_found_in_article", "is_grounded": False}

    # Verify exact quote exists in at least one retrieved chunk
    quote_clean = quote.strip().lower()
    verified = any(quote_clean in c["text"].lower() for c in retrieved)

    if not verified:
        logger.warning(f"Citation verification failed: quote '{quote}' not found in retrieved chunks.")
        return {"answer": "not_found_in_article", "is_grounded": False}

    return {"answer": answer, "is_grounded": True}


workflow = StateGraph(AskArticleState)
workflow.add_node("chunk_and_retrieve", node_chunk_and_retrieve)
workflow.add_node("generate_answer", node_generate_grounded_answer)
workflow.add_node("verify_grounding", node_verify_grounding)

workflow.add_edge(START, "chunk_and_retrieve")
workflow.add_edge("chunk_and_retrieve", "generate_answer")
workflow.add_edge("generate_answer", "verify_grounding")
workflow.add_edge("verify_grounding", END)

app = workflow.compile()


from .simple_chain import run_ask_article_ticket_chain


def run_ask_article_flow(article_text: str, question: str) -> dict:
    return run_ask_article_ticket_chain(article_text=article_text, question=question)

