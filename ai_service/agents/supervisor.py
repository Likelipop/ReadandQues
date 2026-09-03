"""
ai_service/agents/supervisor.py — Central General Agent & Supervisor Node.

Acts as the intelligent orchestrator:
1. Intent recognition & direct platform/reading Q&A.
2. Direct contextual vocabulary/grammar explanation.
3. Autonomous tool-calling to `search_articles` when grounded facts or recommendations are needed.
4. Delegation to Quiz Sub-Agent for reading comprehension assessments.
5. True real-time token streaming with context window management.
All comments and docstrings are in English.
"""

import asyncio
import logging
import re
from typing import Any

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)

from ai_service.agents.memory import (
    format_user_profile_for_prompt,
    generate_rolling_summary,
    get_user_learning_profile,
    should_summarize,
    trim_conversation_history,
    update_user_learning_profile,
)
from ai_service.agents.prompts import (
    HOMEPAGE_CONTEXT_INSTRUCTIONS,
    READSPACE_CONTEXT_INSTRUCTIONS,
    SUPERVISOR_BASE_PROMPT,
)
from ai_service.agents.quiz_agent import run_quiz_subagent
from ai_service.agents.state import StudyDockState
from ai_service.agents.tools import search_articles
from ai_service.connection import get_llm

logger = logging.getLogger(__name__)

# List of tools available to the Supervisor
SUPERVISOR_TOOLS = [search_articles]


def _detect_quick_quiz_intent(query: str) -> bool:
    """Check if query is an explicit request to generate a comprehension quiz."""
    q = query.lower().strip()
    quiz_patterns = [
        r"\b(tạo|cho|làm|ra)\s+(bài\s+)?(quiz|trắc nghiệm|kiểm tra|câu hỏi|đề)\b",
        r"\b(create|generate|make|give me|test me with)\s+(a\s+)?(quiz|test|questions)\b",
        r"\b(quiz\s+me|comprehension\s+quiz)\b",
    ]
    for pattern in quiz_patterns:
        if re.search(pattern, q):
            return True
    return False


def _detect_vocabulary_inquiry(query: str) -> list[str]:
    """Extract vocabulary words user asked about to update LTM tricky_words."""
    q = query.strip()
    # Simple regex to extract quoted words or target phrases
    matches = re.findall(r"['\"]([^'\"]+)['\"]", q)
    if matches:
        return [m.strip().lower() for m in matches if len(m.split()) <= 3]
    return []


async def supervisor_node(state: StudyDockState) -> dict[str, Any]:
    """
    Main Supervisor Node in LangGraph.
    Performs context-aware reasoning, tool calling, and response synthesis.
    """
    messages = state.get("messages", [])
    if not messages:
        return {"messages": [AIMessage(content="Hello! How can I assist you with your reading today?")]}

    page_context = state.get("page_context", "homepage")
    article_id = state.get("article_id", "")
    article_text = state.get("article_text", "")
    user_id = state.get("user_id")

    # 1. Memory & Profile retrieval
    profile = state.get("user_profile") or get_user_learning_profile(user_id)
    conversation_summary = state.get("conversation_summary", "")

    # Check if we should update rolling summary
    if should_summarize(messages):
        conversation_summary = await asyncio.to_thread(
            generate_rolling_summary, messages, conversation_summary
        )

    # 2. Extract last user query
    last_user_msg = next(
        (m for m in reversed(messages) if isinstance(m, HumanMessage)), None
    )
    user_query = last_user_msg.content if last_user_msg and hasattr(last_user_msg, "content") else ""
    if isinstance(user_query, list):
        # Handle list of text blocks if any
        user_query = " ".join([b.get("text", "") if isinstance(b, dict) else str(b) for b in user_query])

    # Record tricky vocabulary in user's LTM profile
    tricky_words_found = _detect_vocabulary_inquiry(str(user_query))
    if tricky_words_found and user_id:
        existing_words = profile.get("tricky_words", [])
        new_words = list(set(existing_words + tricky_words_found))
        profile["tricky_words"] = new_words
        update_user_learning_profile(user_id, {"tricky_words": new_words})

    # 3. Handle direct Quiz Delegation if user explicitly requested quiz
    if _detect_quick_quiz_intent(str(user_query)):
        logger.info(f"[Supervisor] Detected quiz intent for query: '{user_query}'")
        quiz_res = await asyncio.to_thread(
            run_quiz_subagent, article_id=article_id, article_text=article_text
        )
        quizzes = quiz_res.get("quizzes", [])
        error = quiz_res.get("error", "")
        summary = quiz_res.get("summary", "")

        if error or not quizzes:
            err_msg = error or "Could not generate questions from this passage."
            resp_content = (
                f"**⚠️ Cannot generate quiz:** {err_msg}\n\n"
                "Please open an article in **ReadSpace** before generating reading comprehension questions."
            )
            return {
                "messages": [AIMessage(content=resp_content)],
                "intent": "quiz",
                "action_type": "chat",
                "quiz_data": [],
                "error": err_msg,
                "response": resp_content,
            }

        quiz_resp_text = (
            f"### 📝 Reading Comprehension Quiz Ready!\n\n"
            f"I have generated **{len(quizzes)}** reading comprehension questions based on this article.\n\n"
            + (f"**Passage Summary:** {summary}\n\n" if summary else "")
            + "👉 Practice directly using the quiz panel on your right."
        )
        return {
            "messages": [AIMessage(content=quiz_resp_text)],
            "intent": "quiz",
            "action_type": "quiz",
            "quiz_data": quizzes,
            "citations": [],
            "error": "",
            "response": quiz_resp_text,
        }

    # 4. Construct System Prompt based on Page Context
    profile_section = format_user_profile_for_prompt(profile)
    summary_section = (
        f"Key facts from previous turns:\n{conversation_summary}"
        if conversation_summary
        else "No previous context. This is the start of the session."
    )

    if page_context == "readspace":
        page_title = "ReadSpace (Article Reading Workspace)"
        page_instructions = READSPACE_CONTEXT_INSTRUCTIONS.format(
            article_id=article_id or "None",
            article_text=article_text[:5000] if article_text else "No passage text loaded.",
        )
    else:
        page_title = "Homepage / Feed Discovery"
        page_instructions = HOMEPAGE_CONTEXT_INSTRUCTIONS

    system_prompt = SUPERVISOR_BASE_PROMPT.format(
        user_profile_section=profile_section,
        conversation_summary_section=summary_section,
        page_context_title=page_title,
        page_context_instructions=page_instructions,
    )

    # 5. Trim conversation messages to prevent context window overflow
    trimmed_msgs = trim_conversation_history(messages, max_tokens=3500)
    final_messages = [SystemMessage(content=system_prompt)] + [
        m for m in trimmed_msgs if not isinstance(m, SystemMessage)
    ]

    # 6. Bind Tools & Invoke LLM
    llm = get_llm(temperature=1.0)
    llm_with_tools = llm.bind_tools(SUPERVISOR_TOOLS)

    try:
        response = await llm_with_tools.ainvoke(final_messages)
    except Exception as e:
        logger.error(f"[Supervisor] LLM invocation failed: {e}")
        response = AIMessage(content=f"I encountered an error processing your request: {e}")

    # Determine intent for metadata
    intent = "general"
    if getattr(response, "tool_calls", None):
        intent = "rag"
    elif "explain" in str(user_query).lower() or "nghĩa là gì" in str(user_query).lower():
        intent = "explain"

    return {
        "messages": [response],
        "intent": intent,
        "action_type": "chat",
        "conversation_summary": conversation_summary,
        "user_profile": profile,
        "response": response.content if hasattr(response, "content") else str(response),
    }
