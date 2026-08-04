# Service, Data, Orchestration, and AI Refactor

This file is the durable source of truth for the `refactor/service-orchestration`
program. Chat history is context; this roadmap and the current repository state
are authoritative.

## Objective

Refactor ReadAndQues into a maintainable Django service with:

- one canonical article data model and stable cross-store identifiers;
- explicit, versioned initialization and migrations for non-SQL stores;
- typed jobs and pipelines grouped by business capability;
- thin Django views backed by application services;
- a shared, observable AI-tool runtime;
- a grounded, stateless article question-ticket tool;
- tested deployment, backfill, cutover, rollback, and recovery procedures.

## Non-negotiable invariants

1. PostgreSQL owns transactional user and business data.
2. MongoDB owns the canonical article and generated-content document.
3. MinIO is an immutable raw-source archive, not a competing article database.
4. Chroma and BM25 are rebuildable projections and never sources of truth.
5. `article_id` has one meaning across every store and API.
6. Views do not import database collections, graphs, jobs, or registries.
7. Simple reads and writes use application services/repositories, not pipelines.
8. Pipeline and AI failures are explicit; validation never fails open.
9. Data changes follow expand, backfill, validate, cut over, then contract.
10. Legacy data is not deleted without a verified backup and explicit approval.

## Delivery sequence

Each checkbox represents an intended atomic commit. A commit may be split further
when that improves reviewability, but unrelated steps must not be combined.

### PR 1: Baseline and decisions

- [x] RQ-001 Document datastore, orchestration, and AI architecture decisions.
- [x] RQ-002 Characterize the existing registry and pipeline executor.
- [x] RQ-003 Characterize article import, quiz, and paraphrase flows.
- [ ] RQ-004 Add repeatable quality-gate commands.

Gate: existing behavior is covered without live infrastructure.

### PR 2: Package and application boundaries

- [ ] RQ-005 Rename the Django `pipeline` app to `service` atomically.
- [ ] RQ-006 Rename `etl` to `orchestration` atomically.
- [ ] RQ-007 Move engine and registry into `orchestration/configuration`.
- [ ] RQ-008 Introduce application services and remove infrastructure imports from views.

Gate: Django checks pass and views depend only on application services.

### PR 3: Data integrity and migrations

- [ ] RQ-009 Add canonical Pydantic data contracts and state enums.
- [ ] RQ-010 Introduce stable application-generated article identifiers.
- [ ] RQ-011 Add a locked, checksummed non-SQL migration runner.
- [ ] RQ-012 Move Mongo, MinIO, Chroma, and BM25 setup out of imports.
- [ ] RQ-013 Add Mongo validators and required indexes.
- [ ] RQ-014 Make Bronze objects immutable and add versioned manifests.
- [ ] RQ-015 Add canonical repositories with temporary legacy read adapters.
- [ ] RQ-016 Add data audit and idempotent backfill commands.
- [ ] RQ-017 Rebuild projections using canonical IDs and versioned embeddings.

Gate: old data remains readable; new writes are validated and traceable.

### PR 4: Typed orchestration

- [ ] RQ-018 Add typed job, pipeline, context, and result contracts.
- [ ] RQ-019 Add lifecycle context managers, decorators, and structured errors.
- [ ] RQ-020 Add inline and background executor interfaces.
- [ ] RQ-021 Regroup jobs by ingestion, articles, AI, search, and maintenance.
- [ ] RQ-022 Define canonical multi-step business pipelines.
- [ ] RQ-023 Replace orchestration helper functions with a thin facade.
- [ ] RQ-024 Repair the daily pipeline and truthful failure reporting.

Gate: pipelines validate before execution and no one-job query pipelines remain.

### PR 5: Shared AI platform

- [ ] RQ-025 Add explicit providers, model profiles, and a model gateway.
- [ ] RQ-026 Add versioned AI-tool contracts and registry.
- [ ] RQ-027 Add PostgreSQL AI-tool run persistence.
- [ ] RQ-028 Add shared authorization, quota, cache, usage, and error policies.
- [ ] RQ-029 Move smart paraphrase onto the AI-tool runtime.
- [ ] RQ-030 Move quiz generation onto the AI-tool runtime.
- [ ] RQ-031 Move batch paraphrase onto the AI-tool runtime.

Gate: every AI call has a run ID, model/prompt version, usage, and typed outcome.

### PR 6: Grounded question ticket

- [ ] RQ-032 Add stable article chunking and content hashes.
- [ ] RQ-033 Add article-scoped lexical retrieval.
- [ ] RQ-034 Add the ask-article LangGraph workflow.
- [ ] RQ-035 Add exact citation and grounding verification.
- [ ] RQ-036 Add generic authenticated AI-tool run endpoints.
- [ ] RQ-037 Add the one-question ticket UI.
- [ ] RQ-038 Add grounding, injection, failure, and idempotency evaluations.

Gate: answers are restricted to the current article and carry verified citations.

### PR 7: Transactional cutover and operations

- [ ] RQ-039 Add a transactional article-import and star-charge ledger.
- [ ] RQ-040 Migrate exam attempts to PostgreSQL with JSON payloads.
- [ ] RQ-041 Cut reads over to canonical article storage after audit approval.
- [ ] RQ-042 Archive legacy Gold collections without deleting them.
- [ ] RQ-043 Add deployment migration, health, and smoke-test workflow.
- [ ] RQ-044 Document backup, restore, reindex, and failed-run recovery.
- [ ] RQ-045 Remove legacy adapters only after a stable soak release.

Gate: production operations and rollback are documented and tested.

## Verification matrix

Every completed item must identify evidence in `STATUS.md`:

- source files or migration files implementing the requirement;
- focused unit/integration tests;
- commands run and their results;
- data-quality or backfill reports where applicable;
- rollback or compatibility behavior for risky changes;
- unresolved limitations, if any.

The program is complete only when all gates pass and a final audit proves every
invariant above from current repository and runtime evidence.
