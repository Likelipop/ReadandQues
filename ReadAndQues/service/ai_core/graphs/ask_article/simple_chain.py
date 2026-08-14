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
    has_evidence: bool = Field(description="True if the question relates to the article (facts, vocabulary, concepts, summary). Set False ONLY if question is completely unrelated.")
    answer: str = Field(description="Direct answer or vocabulary/concept explanations grounded in the text.")
    citation_quote: Optional[str] = Field(default="", description="Exact quote or key excerpt from the article supporting the answer or vocabulary example.")


def is_learning_or_analytical_query(question: str) -> bool:
    q_lower = question.lower()
    keywords = [
        "vocab", "vocabulary", "concept", "explain", "summary", "summarize", 
        "meaning", "define", "grammar", "difficult", "word", "phrase", "translate",
        "key point", "theme", "overview", "what is this about", "highlight", "analyse", "analyze"
    ]
    return any(kw in q_lower for kw in keywords)


def run_ask_article_ticket_chain(article_text: str, question: str) -> Dict:
    """
    Enhanced LangChain pipeline for single-article Question Ticket resolution.
    Supports both factual Q&A and language learning (vocabulary, concepts, summaries).
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
        # 1. Determine Context: Use full text for learning/vocab queries, top-k chunks for factual queries
        if is_learning_or_analytical_query(question):
            context_str = article_text[:4500]
        else:
            chunks = chunk_article_text(article_text)
            retrieved = retrieve_article_chunks(chunks, question, top_k=3)
            if retrieved:
                context_str = "\n\n".join(f"[{c.chunk_id}] {c.text}" for c in retrieved)
            else:
                context_str = article_text[:4500]

        # 2. Build LangChain Chat Prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "You are an expert AI Reading Assistant & Language Tutor for news and academic articles.\n"
                "Your task is to assist readers with both factual Q&A and language learning (vocabulary, complex concepts, grammar, summaries).\n\n"
                "Instructions:\n"
                "1. For Vocabulary & Concept Requests (e.g. explain vocabulary, difficult words, concepts, summaries):\n"
                "   - Identify key difficult vocabulary, technical terms, or core concepts in the provided article text.\n"
                "   - Explain them clearly with definitions and contextual notes.\n"
                "   - Include an exact sentence from the article in `citation_quote` and set `has_evidence=True`.\n\n"
                "2. For Factual Questions:\n"
                "   - Answer directly and accurately based on the article text.\n"
                "   - Provide the exact supporting sentence in `citation_quote` and set `has_evidence=True`.\n\n"
                "3. Formatting Guidelines:\n"
                "   - ALWAYS format lists using clean Markdown bullet points (`- **Term**: Definition`).\n"
                "   - Avoid continuous walls of text.\n"
                "   - Separate different points or terms with line breaks.\n\n"
                "4. Unrelated Questions:\n"
                "   - ONLY set `has_evidence=False` and `answer='Information not found in the article text.'` if the question is completely unrelated to the article."
            )),
            ("user", "Article Content:\n{context}\n\nUser Question/Request: {question}"),
        ])

        # 3. Invoke LLM with Structured Pydantic Output
        llm = get_llm(temperature=0.1)
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
