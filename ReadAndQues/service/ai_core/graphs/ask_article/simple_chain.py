"""
service/ai_core/graphs/ask_article/simple_chain.py — Streamlined LangChain Question Ticket Chain
"""

import logging
import time
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from langchain_core.prompts import ChatPromptTemplate
from service.ai_core.connection import get_llm
from service.ai_core.grounding import chunk_article_text, retrieve_article_chunks

logger = logging.getLogger(__name__)


class ArticleQuestionTicketSchema(BaseModel):
    has_evidence: bool = Field(description="True if the article contains direct evidence to answer the question.")
    answer: str = Field(description="Direct, concise answer grounded in the article excerpts.")
    citation_quote: Optional[str] = Field(default="", description="Exact quote from the article supporting the answer.")


def run_ask_article_ticket_chain(article_text: str, question: str) -> Dict:
    """
    Simplified LangChain pipeline for single-article Question Ticket resolution.
    Returns a structured Ticket dictionary.
    """
    timestamp_str = datetime.now().strftime("%H:%M:%S")
    ticket_id = f"TKT-{int(time.time()) % 100000:05d}"

    if not article_text or not question:
        return {
            "ticket_id": ticket_id,
            "question": question or "",
            "answer": "Invalid input provided.",
            "citation_quote": "",
            "status": "ERROR",
            "timestamp": timestamp_str,
            "is_grounded": False,
        }

    try:
        # 1. Chunk and Retrieve Excerpts
        chunks = chunk_article_text(article_text)
        retrieved = retrieve_article_chunks(chunks, question, top_k=3)

        if not retrieved:
            return {
                "ticket_id": ticket_id,
                "question": question,
                "answer": "Information not found in the article text.",
                "citation_quote": "",
                "status": "NOT_FOUND",
                "timestamp": timestamp_str,
                "is_grounded": False,
            }

        context_str = "\n\n".join(f"[{c.chunk_id}] {c.text}" for c in retrieved)

        # 2. Build LangChain Chat Prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "You are an AI Question Ticket Resolution assistant for news articles.\n"
                "Answer the user's question strictly using the provided article excerpts below.\n"
                "Constraints:\n"
                "1. If the exact answer cannot be verified from the excerpts, set has_evidence=False and answer='Information not found in the article text.'\n"
                "2. If evidence exists, set has_evidence=True, provide a clear answer, and include the exact supporting quote in citation_quote.\n"
                "3. Do NOT extrapolate or assume information outside the text."
            )),
            ("user", "Excerpts:\n{context}\n\nQuestion: {question}"),
        ])

        # 3. Invoke LLM with Structured Pydantic Output (temperature=0.0)
        llm = get_llm(temperature=0.0)
        structured_llm = llm.with_structured_output(ArticleQuestionTicketSchema)
        chain = prompt | structured_llm

        res: ArticleQuestionTicketSchema = chain.invoke({"context": context_str, "question": question})

        if not res.has_evidence or res.answer == "Information not found in the article text.":
            return {
                "ticket_id": ticket_id,
                "question": question,
                "answer": "Information not found in the article text.",
                "citation_quote": "",
                "status": "NOT_FOUND",
                "timestamp": timestamp_str,
                "is_grounded": False,
            }

        return {
            "ticket_id": ticket_id,
            "question": question,
            "answer": res.answer,
            "citation_quote": res.citation_quote or "",
            "status": "RESOLVED",
            "timestamp": timestamp_str,
            "is_grounded": True,
        }

    except Exception as e:
        logger.error(f"[AskArticleTicketChain] Error: {e}")
        return {
            "ticket_id": ticket_id,
            "question": question,
            "answer": f"System error processing ticket: {str(e)}",
            "citation_quote": "",
            "status": "ERROR",
            "timestamp": timestamp_str,
            "is_grounded": False,
        }
