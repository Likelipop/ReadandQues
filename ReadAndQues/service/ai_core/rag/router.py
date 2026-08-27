"""
service/rag/router.py — LangGraph StateGraph Router for dynamic RAG agent selection.
"""

import json
import logging
import os
import re
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph

from service.ai_core.platform.gateway import ModelGateway
from service.ai_core.rag.agents.news.agent import run_news_agent
from service.ai_core.rag.prompts import ROUTER_INTENT_CLASSIFIER_PROMPT
from service.ai_core.rag.schemas import RAGResponse
from service.domain.enums import AgentIntent

logger = logging.getLogger(__name__)


class RouterState(TypedDict):
    question: str
    article_id: str | None
    intent: str
    confidence: float
    answer: str
    citations: list[dict[str, Any]]
    retrieved_chunks_count: int
    model_used: str


def classify_intent_node(state: RouterState) -> RouterState:
    """Classifies user query intent using ModelGateway with automatic provider fallbacks."""
    question = state.get("question", "")
    article_id = state.get("article_id") or ""

    try:
        llm = ModelGateway.get_llm(profile_name="precise", temperature=0.0)
        prompt = ROUTER_INTENT_CLASSIFIER_PROMPT.format(question=question, article_id=article_id)
        resp = llm.invoke([HumanMessage(content=prompt)])
        content = resp.content if hasattr(resp, "content") else str(resp)

        # Clean potential markdown formatting
        if "```" in content:
            content = re.sub(r"^```(?:json)?|```$", "", content.strip(), flags=re.MULTILINE).strip()

        parsed = json.loads(content)

        raw_intent = parsed.get("intent", "news").lower()
        if raw_intent not in [i.value for i in AgentIntent]:
            raw_intent = AgentIntent.NEWS.value

        state["intent"] = raw_intent
        state["confidence"] = float(parsed.get("confidence", 1.0))
        return state
    except Exception as e:
        logger.warning(f"[RAG Router] Intent classification fallback: {e}. Defaulting to 'news'.")
        state["intent"] = AgentIntent.NEWS.value
        state["confidence"] = 0.5
        return state


def route_intent_edge(state: RouterState) -> str:
    """Conditional edge selector."""
    intent = state.get("intent", "news")
    if intent in ["news", "unknown"]:
        return "news_agent"
    return "news_agent"  # Fallback all to news_agent until teacher agent added


def news_agent_node(state: RouterState) -> RouterState:
    """Node wrapping News Agent execution."""
    question = state["question"]
    article_id = state.get("article_id")
    filters = {"article_id": article_id} if article_id else None

    result = run_news_agent(query=question, filters=filters)

    state["answer"] = result.answer
    state["citations"] = [c.model_dump() for c in result.citations]
    state["retrieved_chunks_count"] = result.retrieved_chunks_count
    state["model_used"] = result.model_used
    return state


def build_rag_router_graph():
    """Builds and compiles LangGraph StateGraph router."""
    workflow = StateGraph(RouterState)

    workflow.add_node("classify_intent", classify_intent_node)
    workflow.add_node("news_agent", news_agent_node)

    workflow.set_entry_point("classify_intent")
    workflow.add_conditional_edges("classify_intent", route_intent_edge, {"news_agent": "news_agent"})
    workflow.add_edge("news_agent", END)

    return workflow.compile()


_rag_router_app = None


def get_rag_router():
    global _rag_router_app
    if _rag_router_app is None:
        _rag_router_app = build_rag_router_graph()
    return _rag_router_app


def execute_rag_pipeline(question: str, article_id: str | None = None) -> RAGResponse:
    """Executes the LangGraph RAG router."""
    app = get_rag_router()

    initial_state: RouterState = {
        "question": question,
        "article_id": article_id,
        "intent": "unknown",
        "confidence": 0.0,
        "answer": "",
        "citations": [],
        "retrieved_chunks_count": 0,
        "model_used": "gpt-4o-mini",
    }

    final_state = app.invoke(initial_state)

    intent_enum = AgentIntent(final_state.get("intent", "news"))

    return RAGResponse(
        status="success",
        query=question,
        intent=intent_enum,
        answer=final_state.get("answer", ""),
        citations=final_state.get("citations", []),
        retrieved_chunks_count=final_state.get("retrieved_chunks_count", 0),
        model_used=final_state.get("model_used", "gpt-4o-mini"),
    )
