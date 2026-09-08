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
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1.0)
                sock.connect((db_host, int(db_port)))
                sock.close()
            except Exception as se:
                raise ConnectionError(f"Database host {db_host}:{db_port} not reachable: {se}")

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


def _approx_token_count(msgs: list[BaseMessage]) -> int:
    """Approximate token count using word-based heuristic (~1.33 tokens per word)."""
    total = 0
    for m in msgs:
        content = m.content if hasattr(m, "content") else str(m)
        if isinstance(content, str):
            total += len(content.split()) * 4 // 3
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    total += len(block.get("text", "").split()) * 4 // 3
                else:
                    total += len(str(block).split()) * 4 // 3
    return total


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
            token_counter=_approx_token_count,  # Word/approx token counter for speed & reliability
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


from pydantic import BaseModel, Field

class VocabularyUpdate(BaseModel):
    """Structured extraction of linguistic items the user asked about."""
    lexical_items: list[str] = Field(default_factory=list, description="Single words (e.g., ubiquitous, ephemeral)")
    phrasal_verbs: list[str] = Field(default_factory=list, description="Phrasal verbs (e.g., make up, look forward to)")
    collocations: list[str] = Field(default_factory=list, description="Common word combinations (e.g., heavy rain, commit a crime)")
    idioms: list[str] = Field(default_factory=list, description="Idiomatic expressions (e.g., once in a blue moon)")
    grammar_patterns: list[str] = Field(default_factory=list, description="Grammar structures (e.g., Inversion, Conditional)")

class SessionSummary(BaseModel):
    """The structured output of the rolling summarizer."""
    conversation_summary: str = Field(description="Brief factual summary of the chat so far")
    vocabulary: VocabularyUpdate = Field(description="Linguistic items the user struggled with or asked about")
    weak_skills: list[str] = Field(default_factory=list, description="Reading skills the user struggled with")
    learning_notes: str = Field(description="Observations about the user's learning behavior or goals")

def generate_rolling_summary(
    messages: list[BaseMessage], existing_summary: str = ""
) -> SessionSummary | None:
    """
    Generate a concise factual rolling summary of older conversation turns
    and extract vocabulary/skills using LLM structured output.
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
            return None

        llm = get_llm()
        structured_llm = llm.with_structured_output(SessionSummary)
        prompt = ROLLING_SUMMARIZER_PROMPT.format(messages_text="\n".join(dialogue_lines))
        
        # We need to pass it as a message to structured_llm
        resp = structured_llm.invoke([HumanMessage(content=prompt)])
        return resp
    except Exception as e:
        logger.warning(f"[Memory] Failed to generate structured rolling summary: {e}")
        return None


# ── Long-Term Memory (User Learning Profile) ──────────────────────────────────

_LTM_CACHE: dict[int, dict[str, Any]] = {}


def get_default_user_profile() -> dict[str, Any]:
    """Default learning profile for new or unauthenticated users."""
    return {
        "cefr_level": "B1",
        "interests": ["General", "Technology", "Education"],
        "weak_skills": ["TrueFalseNotgiven", "Inference"],
        "vocabulary_profile": {
            "lexical_items": [],
            "phrasal_verbs": [],
            "collocations": [],
            "idioms": [],
            "grammar_patterns": []
        },
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
        from ai_service.adapters import get_mongo_client
        client = get_mongo_client()
        if client:
            db = client.get_default_database()
            doc = db["user_learning_profiles"].find_one({"user_id": user_id})
            if doc:
                profile.update({
                    "cefr_level": doc.get("cefr_level", "B1"),
                    "interests": doc.get("interests", ["General"]),
                    "weak_skills": doc.get("weak_skills", ["TrueFalseNotgiven"]),
                    "vocabulary_profile": doc.get("vocabulary_profile", profile["vocabulary_profile"]),
                    "reading_notes": doc.get("reading_notes", ""),
                    "language_preference": doc.get("language_preference", "Bilingual En-Vi"),
                })
    except Exception as e:
        logger.debug(f"[Memory] Could not load profile from MongoDB ({e}). Using default.")

    _LTM_CACHE[user_id] = profile
    return profile


def update_user_learning_profile(user_id: int | None, updates: dict[str, Any]) -> None:
    """
    Update user learning profile in cache and persist asynchronously.
    """
    if not user_id:
        return

    profile = get_user_learning_profile(user_id)
    
    # Handle deep merge for vocabulary_profile if present
    if "vocabulary_profile" in updates:
        vocab_updates = updates.pop("vocabulary_profile")
        for k, v in vocab_updates.items():
            if isinstance(v, list):
                # Merge lists and remove duplicates
                current_list = profile["vocabulary_profile"].get(k, [])
                profile["vocabulary_profile"][k] = list(set(current_list + v))

    profile.update(updates)
    _LTM_CACHE[user_id] = profile

    try:
        from ai_service.adapters import get_mongo_client
        client = get_mongo_client()
        if client:
            db = client.get_default_database()
            db["user_learning_profiles"].update_one(
                {"user_id": user_id},
                {"$set": profile},
                upsert=True,
            )
    except Exception as e:
        logger.debug(f"[Memory] Could not persist profile update to MongoDB: {e}")


def format_user_profile_for_prompt(profile: dict[str, Any]) -> str:
    """Format user profile as clean markdown for system prompt injection."""
    cefr = profile.get("cefr_level", "B1")
    interests = ", ".join(profile.get("interests", ["General"]))
    weak_skills = ", ".join(profile.get("weak_skills", ["TrueFalseNotgiven"]))
    
    vocab_profile = profile.get("vocabulary_profile", {})
    vocab_lines = []
    for category, items in vocab_profile.items():
        if items:
            # Show up to 5 most recent items per category
            recent_items = items[-5:]
            vocab_lines.append(f"  - {category.replace('_', ' ').title()}: {', '.join(recent_items)}")
            
    vocab_str = "\n".join(vocab_lines) if vocab_lines else "  - None recorded yet"
    notes = profile.get("reading_notes", "")[:200]
    lang_pref = profile.get("language_preference", "En")

    return (
        f"- Target CEFR Reading Level: {cefr}\n"
        f"- Topics of Interest: {interests}\n"
        f"- Challenging Question Types: {weak_skills}\n"
        f"- Recent Tricky Language Items:\n{vocab_str}\n"
        f"- Reading Needs Note: {notes}\n"
        f"- Preferred Explanation Style: {lang_pref}"
    )
