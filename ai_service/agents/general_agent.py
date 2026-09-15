"""
ai_service/agents/general_agent.py — General-Purpose ReAct Agent Node.

Handles all non-quiz interactions:
- Direct vocabulary/grammar explanations
- Article discussion and comprehension
- Tool-calling to search_articles for grounded facts and recommendations
- Platform guidance
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
from ai_service.agents.state import StudyDockState
from ai_service.agents.tools import search_articles
from ai_service.connection import get_llm

logger = logging.getLogger(__name__)

# Tools available to the General Agent
GENERAL_AGENT_TOOLS = [search_articles]




async def general_agent_node(state: StudyDockState) -> dict[str, Any]:
    """
    General-purpose ReAct agent node.
    Performs context-aware reasoning, tool calling, and response synthesis.
    Intent has already been classified by the router node.
    """
    messages = state.get("messages", [])
    if not messages:
        return {
            "messages": [AIMessage(content="Hello! How can I assist you with your reading today?")],
            "action_type": "chat",
            "response": "Hello! How can I assist you with your reading today?",
        }

    page_context = state.get("page_context", "homepage")
    article_id = state.get("article_id", "")
    article_text = state.get("article_text", "")
    user_id = state.get("user_id")

    # 1. Memory & Profile retrieval
    profile = state.get("user_profile") or get_user_learning_profile(user_id)
    conversation_summary = state.get("conversation_summary", "")

    # 2. Extract last user query
    last_user_msg = next(
        (m for m in reversed(messages) if isinstance(m, HumanMessage)), None
    )
    user_query = last_user_msg.content if last_user_msg and hasattr(last_user_msg, "content") else ""
    if isinstance(user_query, list):
        user_query = " ".join(
            b.get("text", "") if isinstance(b, dict) else str(b) for b in user_query
        )

    # 3. Rolling Summary & LTM Profile Updates
    if should_summarize(messages):
        summary_result = await asyncio.to_thread(
            generate_rolling_summary, messages, conversation_summary
        )
        if summary_result:
            # Update short-term conversation context
            conversation_summary = summary_result.conversation_summary
            
            # Prepare long-term memory updates
            profile_updates = {}
            if summary_result.learning_notes:
                profile_updates["reading_notes"] = summary_result.learning_notes
            if summary_result.weak_skills:
                current_weak = profile.get("weak_skills", [])
                profile_updates["weak_skills"] = list(set(current_weak + summary_result.weak_skills))
            if summary_result.vocabulary:
                profile_updates["vocabulary_profile"] = summary_result.vocabulary.dict()

            if profile_updates and user_id:
                update_user_learning_profile(user_id, profile_updates)
                # Refresh local profile variable for the prompt
                profile = get_user_learning_profile(user_id)

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
    llm = get_llm()
    llm_with_tools = llm.bind_tools(GENERAL_AGENT_TOOLS)

    try:
        response = await llm_with_tools.ainvoke(final_messages)
    except Exception as e:
        logger.error(f"[GeneralAgent] LLM invocation failed: {e}")
        response = AIMessage(content=f"I encountered an error processing your request: {e}")

    return {
        "messages": [response],
        "action_type": "chat",
        "conversation_summary": conversation_summary,
        "user_profile": profile,
        "response": response.content if hasattr(response, "content") else str(response),
    }
