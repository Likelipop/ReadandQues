# ADR-0001: Datastore Ownership and Consistency

Status: accepted

## Context

The application currently stores overlapping article representations in MongoDB,
MinIO, Chroma, and an in-memory BM25 index. PostgreSQL user records are referenced
from MongoDB without enforceable relationships. Split and legacy Gold collections
compete as article sources of truth.

## Decision

- PostgreSQL owns users, entitlements, import requests, attempts, and AI run ledgers.
- MongoDB owns one canonical article document and reusable generated artifacts.
- MinIO stores immutable raw source objects plus versioned manifests.
- Chroma and BM25 are derived indexes that can be rebuilt from canonical data.
- A stable application-generated `article_id` joins data across stores.
- Cross-store work uses idempotency, explicit states, retries, and compensation;
  it does not pretend to provide a distributed ACID transaction.

Logical Bronze, Silver, and Gold stages may exist without physically duplicating
every stage. Silver is persisted only when replay or audit requirements justify it.

## Consequences

- Legacy collections require an expand/backfill/cutover migration.
- Search and homepage data become projections.
- Data access is mediated through validating repositories.
- Store initialization and schema changes require versioned migrations.
