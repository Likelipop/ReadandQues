"""
ai_service/interface.py — Public API contract for the AI Service.

This is the SINGLE integration boundary between the AI Service and external callers
(Django Backend, Dagster Data Pipeline, evaluation scripts).

ALL comments and docstrings are in English.
"""

from __future__ import annotations

from typing import Any, AsyncGenerator, Generator


def generate_quiz(article_text: str) -> dict[str, Any]:
    """
    Generate IELTS-style reading comprehension questions and extract keywords.

    Args:
        article_text: Plain text content of the article.

    Returns:
        dict with keys: keywords (list[str]), summary (str), questions (list of question dicts).
    """
    from ai_service.quiz_generator.generator import run_question_generator_flow
    return run_question_generator_flow(article_text)


def explain_phrase(phrase: str, context: str = "") -> dict[str, Any]:
    """
    Explain a word or phrase in its surrounding context.

    Args:
        phrase: The word or phrase to explain.
        context: The surrounding paragraph for contextual understanding.

    Returns:
        dict with keys: summary, detailed_explanation, simplified_version, key_terms.
    """
    from ai_service.explainer.explainer import run_explained_flow
    return run_explained_flow(phrase=phrase, paragraph_context=context)


def stream_explanation(phrase: str, context: str = "") -> Generator[str]:
    """
    Stream token-by-token explanation for real-time frontend display.

    Args:
        phrase: The word or phrase to explain.
        context: The surrounding paragraph for context.

    Yields:
        str chunks of the explanation as they are generated.
    """
    from ai_service.explainer.explainer import stream_explained_tokens
    yield from stream_explained_tokens(phrase=phrase, paragraph_context=context)


def ask_question(question: str, article_id: str | None = None) -> dict[str, Any]:
    """
    Answer a question using the multi-agent RAG pipeline.

    Args:
        question: User query in English or Vietnamese.
        article_id: Optional article ID to restrict retrieval scope.

    Returns:
        dict with keys: answer (markdown string), citations (list of dicts).
    """
    from ai_service.rag import execute_rag_pipeline
    result = execute_rag_pipeline(question=question, article_id=article_id)
    return {
        "answer": result.answer,
        "citations": [c if isinstance(c, dict) else c.model_dump() for c in result.citations],
        "retrieved_chunks_count": result.retrieved_chunks_count,
        "intent": result.intent.value if hasattr(result.intent, "value") else str(result.intent),
    }


def search_articles(query: str, method: str = "hybrid", limit: int = 10) -> list[dict[str, Any]]:
    """
    Search articles by keyword (BM25), semantic vector (ChromaDB), or hybrid.

    Args:
        query: Search query string.
        method: One of 'keyword', 'semantic', or 'hybrid'.
        limit: Maximum number of results to return.

    Returns:
        List of dicts with keys: article_id, title, score.
    """
    if method == "keyword":
        from ai_service.rag.search.bm25_index import process_text_to_tokens, search_bm25
        tokens = process_text_to_tokens(query)
        return search_bm25(tokens, n=limit)
    elif method == "semantic":
        from ai_service.rag.search.vector_store import search_by_text
        return search_by_text(query, limit=limit)
    else:
        from ai_service.rag.search.bm25_index import process_text_to_tokens, search_bm25
        from ai_service.rag.search.vector_store import search_by_text
        semantic = search_by_text(query, limit=limit)
        tokens = process_text_to_tokens(query)
        keyword = search_bm25(tokens, n=limit)
        seen = set()
        merged = []
        for item in semantic + keyword:
            aid = item.get("article_id") or item.get("id")
            if aid and aid not in seen:
                seen.add(aid)
                merged.append(item)
        return merged[:limit]


def index_article(
    article_id: str,
    title: str,
    text: str,
    url: str = "",
    keywords: list[str] | None = None,
) -> bool:
    """
    Index an article into ChromaDB and BM25 search indices.

    Called by the data pipeline after creating a Gold article.

    Args:
        article_id: Unique article identifier.
        title: Article title.
        text: Full cleaned article text.
        url: Source URL.
        keywords: Article keywords and topic tags.

    Returns:
        True if indexing succeeded.
    """
    from ai_service.rag.search.bm25_index import rebuild_index
    from ai_service.rag.search.vector_store import add_article_vector, upsert_article_chunks

    add_article_vector(
        gold_id=article_id,
        summary=title,
        title=title,
        url=url,
        keywords=keywords,
    )
    upsert_article_chunks(
        article_id=article_id,
        title=title,
        full_text=text,
        url=url,
        keywords=keywords,
    )
    rebuild_index()
    return True


def get_passage_proof(article_id: str, question_idx: int) -> dict[str, Any] | None:
    """
    Find verbatim passage proof for a specific quiz question.

    Args:
        article_id: The article ID.
        question_idx: Index of the question in the quiz list.

    Returns:
        dict with proof data or None if not found.
    """
    from ai_service.rag.grounding import get_passage_proof as _get_proof
    return _get_proof(article_id=article_id, question_idx=question_idx)


async def stream_study_dock(
    query: str,
    article_id: str = "",
    page_context: str = "homepage",
    article_text: str = "",
    thread_id: str = "",
    user_id: int | None = None,
) -> AsyncGenerator[dict[str, Any]]:
    """
    Asynchronous streaming entry point for the Left AI Study Dock multi-agent system.
    Executes LangGraph via astream_events(v2) and yields structured SSE event payloads
    with TRUE REAL-TIME token streaming (no artificial buffering or delays).

    Yields:
        dict: SSE-ready events containing metadata, text deltas, or final metadata.
    """
    from langchain_core.messages import HumanMessage

    from ai_service.agents.graph import get_study_graph
    from ai_service.agents.state import StudyDockState

    initial_state: StudyDockState = {
        "messages": [HumanMessage(content=query)],
        "article_id": article_id,
        "page_context": page_context,
        "article_text": article_text,
        "user_id": user_id,
        "conversation_summary": "",
        "user_profile": {},
        "intent": "general",
        "response": "",
        "citations": [],
        "quiz_data": [],
        "action_type": "chat",
        "error": "",
    }

    import uuid
    if not thread_id:
        thread_id = f"thread_{uuid.uuid4().hex[:12]}"
    config = {"configurable": {"thread_id": thread_id}}

    graph = get_study_graph()
    emitted_token_count = 0
    final_output: dict[str, Any] = {}

    # Yield initial metadata event
    yield {
        "type": "metadata",
        "intent": "general",
        "action_type": "chat",
        "citations": [],
        "quiz_data": [],
        "error": "",
    }

    async for event in graph.astream_events(initial_state, config=config, version="v2"):
        kind = event.get("event", "")

        # 1. Native token chunk from Chat Model -> Stream delta immediately (True Streaming!)
        if kind == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            content = chunk.content if hasattr(chunk, "content") else (chunk if isinstance(chunk, str) else "")
            # Exclude function/tool call arguments from visible user text deltas
            if content and not getattr(chunk, "tool_call_chunks", None):
                emitted_token_count += 1
                yield {
                    "type": "delta",
                    "text": content,
                }

        # 2. Entire LangGraph execution finished -> Save final state output
        elif kind == "on_chain_end" and event.get("name") == "LangGraph":
            out = event.get("data", {}).get("output", {})
            if isinstance(out, dict):
                final_output = out

    # Final metadata emission
    resp_text = final_output.get("response", "").strip()
    if not resp_text and final_output.get("messages"):
        last_msg = final_output["messages"][-1]
        resp_text = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

    # If no tokens were streamed (e.g. static quiz generation response), emit response as a delta
    if emitted_token_count == 0 and resp_text:
        yield {
            "type": "delta",
            "text": resp_text,
        }

    yield {
        "type": "metadata_final",
        "response": resp_text,
        "citations": final_output.get("citations", []),
        "quiz_data": final_output.get("quiz_data", []),
        "action_type": final_output.get("action_type", "chat"),
        "intent": final_output.get("intent", "general"),
        "error": final_output.get("error", ""),
    }

    yield {"type": "done"}


def stream_study_dock_sync(
    query: str,
    article_id: str = "",
    page_context: str = "homepage",
    article_text: str = "",
    thread_id: str = "",
    user_id: int | None = None,
) -> Generator[dict[str, Any]]:
    """
    Synchronous generator bridge for stream_study_dock.
    Enables immediate token-by-token streaming in WSGI / gthread environments.
    """
    import asyncio

    loop = asyncio.new_event_loop()
    async_gen = stream_study_dock(
        query=query,
        article_id=article_id,
        page_context=page_context,
        article_text=article_text,
        thread_id=thread_id,
        user_id=user_id,
    )
    try:
        while True:
            try:
                event = loop.run_until_complete(async_gen.__anext__())
                yield event
            except StopAsyncIteration:
                break
    finally:
        loop.close()


def ask_study_dock(
    query: str,
    article_id: str = "",
    page_context: str = "homepage",
    article_text: str = "",
    thread_id: str = "",
    user_id: int | None = None,
) -> dict[str, Any]:
    """
    Unified entry point for the Left AI Study Dock multi-agent system.
    Routes query through LangGraph with supervisor and checkpointer memory.
    Synchronously invokes the compiled async LangGraph workflow.

    Args:
        query: User message or query.
        article_id: Optional ID of the currently open article.
        page_context: Current UI context ("readspace", "homepage", "all_tests").
        article_text: Optional plain text of current article if available.
        thread_id: Optional conversation thread ID for persistent memory.
        user_id: Optional authenticated user ID for profile personalization.

    Returns:
        dict with keys: response (markdown), citations (list), quiz_data (list),
                        action_type ("chat" | "quiz"), intent (str), error (str).
    """
    from asgiref.sync import async_to_sync
    from langchain_core.messages import HumanMessage

    from ai_service.agents.graph import get_study_graph
    from ai_service.agents.state import StudyDockState

    initial_state: StudyDockState = {
        "messages": [HumanMessage(content=query)],
        "article_id": article_id,
        "page_context": page_context,
        "article_text": article_text,
        "user_id": user_id,
        "conversation_summary": "",
        "user_profile": {},
        "intent": "general",
        "response": "",
        "citations": [],
        "quiz_data": [],
        "action_type": "chat",
        "error": "",
    }

    import uuid
    if not thread_id:
        thread_id = f"thread_{uuid.uuid4().hex[:12]}"
    config = {"configurable": {"thread_id": thread_id}}

    graph = get_study_graph()
    runner = async_to_sync(graph.ainvoke)
    final_state = runner(initial_state, config=config)

    resp_text = final_state.get("response", "")
    if not resp_text and final_state.get("messages"):
        last_msg = final_state["messages"][-1]
        resp_text = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

    return {
        "response": resp_text,
        "citations": final_state.get("citations", []),
        "quiz_data": final_state.get("quiz_data", []),
        "action_type": final_state.get("action_type", "chat"),
        "intent": final_state.get("intent", "general"),
        "error": final_state.get("error", ""),
    }

