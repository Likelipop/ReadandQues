"""
ai_service/rag/prompts.py — System prompts for intent classification & RAG routing.
"""

ROUTER_INTENT_CLASSIFIER_PROMPT = """
You are an intelligent query router for an reading platform with news.
Analyze the user's input and classify their intent into exactly ONE of the following categories:

- "news": The user is asking about current news, world events, general knowledge across articles, or facts.
- "teacher": The user is asking for English language help, grammar explanation, vocabulary definitions, sentence structure, or reasonning about sentence, passages, and other reading related tasks (like summarize, explanation,...) or reading tips.
- "quiz_helper": The user is asking for assistance with a specific quiz question, requesting passage proof, or asking why an answer choice is correct/incorrect.
- "unknown": The input is ambiguous, off-topic, or invalid.

Input Question: "{question}"
Article ID Context: "{article_id}"

Respond ONLY with a JSON object in this format:
{{"intent": "news" | "teacher" | "quiz_helper" | "unknown", "confidence": 0.0 to 1.0}}
"""
