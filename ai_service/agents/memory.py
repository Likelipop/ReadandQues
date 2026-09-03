"""
ai_service/agents/memory.py — Memory Layer & Context Window Management.

Implements:
1. PostgresSaver checkpointer for thread-scoped short-term conversation memory (with in-memory fallback).
2. Tiered context window manager using `trim_messages` and rolling summarization.
3. UserLearningProfile LTM schema and storage (CEFR level, weak skills with TrueFalseNotgiven, tricky vocab, reading notes).
All comments and docstrings are in English.
"""

import logging
import os
from typing import Any

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    trim_messages,
)
from langgraph.checkpoint.memory import MemorySaver

from ai_service.agents.prompts import ROLLING_SUMMARIZER_PROMPT
from ai_service.connection import get_llm

logger = logging.getLogger(__name__)

# Global singleton checkpointer
_checkpointer = None


def get_checkpointer():
    """
    Initialize and return persistent checkpointer.
    Attempts PostgresSaver first using environment credentials;
    falls back cleanly to MemorySaver for unit tests and offline development.
    """
    global _checkpointer
    if _checkpointer is not None:
        return _checkpointer

    use_postgres = os.getenv("USE_POSTGRES_CHECKPOINTER", "true").lower() in ("true", "1", "yes")

    if use_postgres:
        try:
            import socket
            db_user = os.getenv("DB_USER", "myuser")
            db_pass = os.getenv("DB_PASSWORD", "mypassword")
            db_host = os.getenv("DB_HOST", "postgres")
            db_port = int(os.getenv("DB_PORT", "5432"))
            db_name = os.getenv("DB_NAME", "readandques")

            # Fast host check to avoid hanging connection pool retries
            try:
                socket.getaddrinfo(db_host, db_port, timeout=1.0)
            except Exception as se:
                raise ConnectionError(f"Database host {db_host}:{db_port} not resolvable: {se}")

            from langgraph.checkpoint.postgres import PostgresSaver
            from psycopg_pool import ConnectionPool

            conn_uri = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
            pool = ConnectionPool(conninfo=conn_uri, max_size=10, timeout=2.0, open=True)

            with pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")

            checkpointer = PostgresSaver(pool)
            checkpointer.setup()
            logger.info("[Memory] Successfully initialized PostgresSaver checkpointer.")
            _checkpointer = checkpointer
            return _checkpointer

        except Exception as e:
            logger.info(f"[Memory] PostgresSaver unavailable ({e}). Using MemorySaver fallback.")

    _checkpointer = MemorySaver()
    return _checkpointer


# ── Context Window Management ─────────────────────────────────────────────────


def trim_conversation_history(
    messages: list[BaseMessage], max_tokens: int = 3500
) -> list[BaseMessage]:
    """
    Trim conversation messages using LangChain's trim_messages.
    Guarantees the prompt fits comfortably within the LLM context window while
    preserving the most recent conversation turns and system message.
    """
    if not messages:
        return []

    try:
        # Keep last messages up to max_tokens budget
        trimmed = trim_messages(
            messages,
            max_tokens=max_tokens,
            strategy="last",
            token_counter=len,  # Word/approx token counter for speed & reliability
            allow_partial=False,
            include_system=True,
        )
        return list(trimmed)
    except Exception as e:
        logger.warning(f"[Memory] Failed to trim messages ({e}). Truncating to last 8 messages.")
        # Fallback: keep first system message (if any) + last 8 messages
        system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
        other_msgs = [m for m in messages if not isinstance(m, SystemMessage)]
        return system_msgs[:1] + other_msgs[-8:]


def should_summarize(messages: list[BaseMessage], threshold: int = 8) -> bool:
    """Return True if message count exceeds the summarization threshold."""
    non_system = [m for m in messages if not isinstance(m, SystemMessage)]
    return len(non_system) >= threshold


def generate_rolling_summary(
    messages: list[BaseMessage], existing_summary: str = ""
) -> str:
    """
    Generate a concise factual rolling summary of older conversation turns.
    Preserves discussed topics, tricky vocabulary, and weak skills.
    """
    try:
        dialogue_lines = []
        if existing_summary:
            dialogue_lines.append(f"Previous Context: {existing_summary}")

        for msg in messages[:-4]:  # Summarize everything except the last 4 turns
            role = "User" if isinstance(msg, HumanMessage) else "Assistant"
            content = msg.content if hasattr(msg, "content") else str(msg)
            dialogue_lines.append(f"{role}: {content[:300]}")

        if not dialogue_lines:
            return existing_summary

        llm = get_llm(temperature=1.0)
        prompt = ROLLING_SUMMARIZER_PROMPT.format(messages_text="\n".join(dialogue_lines))
        resp = llm.invoke([HumanMessage(content=prompt)])
        summary = resp.content if hasattr(resp, "content") else str(resp)
        return summary.strip()
    except Exception as e:
        logger.warning(f"[Memory] Failed to generate rolling summary: {e}")
        return existing_summary


# ── Long-Term Memory (User Learning Profile) ──────────────────────────────────

_LTM_CACHE: dict[int, dict[str, Any]] = {}


def get_default_user_profile() -> dict[str, Any]:
    """Default learning profile for new or unauthenticated users."""
    return {
        "cefr_level": "B1",
        "interests": ["General", "Technology", "Education"],
        "weak_skills": ["TrueFalseNotgiven", "Inference"],
        "tricky_words": [],
        "reading_notes": "Learner is currently developing comprehension of academic syntax and inference questions.",
        "language_preference": "Bilingual En-Vi",
    }


def get_user_learning_profile(user_id: int | None) -> dict[str, Any]:
    """
    Retrieve user learning profile from cache / DB.
    """
    if not user_id:
        return get_default_user_profile()

    if user_id in _LTM_CACHE:
        return _LTM_CACHE[user_id]

    profile = get_default_user_profile()

    # Try fetching from Mongo article store client if available
    try:
        try:
            import service.infrastructure.mongo.article_store as article_store
            client = article_store.get_mongo_client()
            db = client.get_default_database()
            doc = db["user_learning_profiles"].find_one({"user_id": user_id})
            if doc:
                profile.update({
                    "cefr_level": doc.get("cefr_level", "B1"),
                    "interests": doc.get("interests", ["General"]),
                    "weak_skills": doc.get("weak_skills", ["TrueFalseNotgiven"]),
                    "tricky_words": doc.get("tricky_words", []),
                    "reading_notes": doc.get("reading_notes", ""),
                    "language_preference": doc.get("language_preference", "Bilingual En-Vi"),
                })
        except Exception as e:
            logger.debug(f"[Memory] Could not load profile from MongoDB ({e}). Using default.")
    except Exception:
        pass

    _LTM_CACHE[user_id] = profile
    return profile


def update_user_learning_profile(user_id: int | None, updates: dict[str, Any]) -> None:
    """
    Update user learning profile in cache and persist asynchronously.
    """
    if not user_id:
        return

    profile = get_user_learning_profile(user_id)
    profile.update(updates)
    _LTM_CACHE[user_id] = profile

    try:
        try:
            import service.infrastructure.mongo.article_store as article_store
            client = article_store.get_mongo_client()
            db = client.get_default_database()
            db["user_learning_profiles"].update_one(
                {"user_id": user_id},
                {"$set": profile},
                upsert=True,
            )
        except Exception as e:
            logger.debug(f"[Memory] Could not persist profile update to MongoDB: {e}")
    except Exception:
        pass


def format_user_profile_for_prompt(profile: dict[str, Any]) -> str:
    """Format user profile as clean markdown for system prompt injection."""
    cefr = profile.get("cefr_level", "B1")
    interests = ", ".join(profile.get("interests", ["General"]))
    weak_skills = ", ".join(profile.get("weak_skills", ["TrueFalseNotgiven"]))
    tricky_words = ", ".join(profile.get("tricky_words", [])[-10:]) or "None recorded yet"
    notes = profile.get("reading_notes", "")[:200]
    lang_pref = profile.get("language_preference", "Bilingual En-Vi")

    return (
        f"- Target CEFR Reading Level: {cefr}\n"
        f"- Topics of Interest: {interests}\n"
        f"- Challenging Question Types: {weak_skills}\n"
        f"- Recent Tricky Words: {tricky_words}\n"
        f"- Reading Needs Note: {notes}\n"
        f"- Preferred Explanation Style: {lang_pref}"
    )
