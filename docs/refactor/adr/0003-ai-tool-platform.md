# ADR-0003: Versioned AI-Tool Platform

Status: accepted

## Context

Quiz, paraphrase, and future reading tools currently use different execution,
persistence, retry, and error paths. Django views and orchestration code know
specific graph details.

## Decision

AI capabilities are versioned tools sharing one runtime. A tool declares:

- name and version;
- typed input and output;
- model profile and prompt version;
- synchronous or submitted execution mode;
- quota, idempotency, and cache policy;
- a LangGraph workflow when branching or validation is useful.

LangChain supplies models, prompts, structured output, and retrieval components.
LangGraph coordinates state transitions, validation, and bounded retries. Simple
one-call features may remain a single node behind the same tool contract.

The question-ticket feature is stateless and article-scoped. It retrieves only
from the current article, produces one answer with exact citations, and returns
`not_found_in_article` when evidence is absent. It is not a chatbot or autonomous
agent.

## Consequences

- Django calls an AI application service, not graphs.
- Every invocation has a persisted run, usage, versions, timing, and typed result.
- Validation failures never become successful answers.
- Chroma is optional for the first article-scoped retrieval implementation.
