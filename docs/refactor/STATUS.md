# Refactor Status Ledger

This ledger is updated after each commit. It records evidence and the next safe
action so work can resume without relying on conversation memory.

## Current state

- Branch: `refactor/service-orchestration`
- Program status: active
- Current gate: PR 1 — baseline and architecture decisions
- Current item: Release Gate 1 verification
- Last verified commit: `54a6290`
- Worktree at program start: clean

## Decision index

- [ADR-0001](adr/0001-data-ownership.md): datastore ownership and consistency
- [ADR-0002](adr/0002-application-orchestration-boundary.md): layer boundaries
- [ADR-0003](adr/0003-ai-tool-platform.md): AI-tool and LangGraph architecture

## Progress log

### 2026-08-04 — Program initialization

- Created the persistent thread goal.
- Confirmed the requested refactor branch is active and clean.
- Confirmed there is no dedicated orchestration/data/AI test suite.
- Began Release Gate 1.

Next action: commit RQ-001, then add characterization tests for the existing
registry and pipeline executor.

### 2026-08-04 — RQ-001 architecture decisions

- Commit: `54a6290 docs: define refactor architecture and delivery roadmap`
- Added the master 45-item delivery sequence and verification rules.
- Accepted datastore ownership, layer-boundary, and AI-tool ADRs.
- Verification: `git diff --check` passed before commit.

Next action: characterize the existing registry and pipeline executor without
requiring live databases or AI providers.

### 2026-08-04 — RQ-002 legacy engine characterization

- Added nine isolated tests for registry metadata, lookup, construction-time
  registration, context propagation, tuple/dictionary outputs, missing inputs,
  exception handling, and stop-on-failure behavior.
- Explicitly captured the current silent duplicate-name replacement behavior.
- Verification: `python -m unittest pipeline.tests.test_pipeline_engine -v`
  passed all nine tests without live infrastructure.

Next action: characterize article import, AI-only quiz generation, and smart
paraphrase application flows with mocked infrastructure.

### 2026-08-04 — RQ-003 workflow characterization

- Added seven infrastructure-free tests around single-article processing,
  crawl failure, orchestrator delegation, AI-only generation/indexing, daemon
  thread submission, and smart-paraphrase cache hit/miss behavior.
- Verification: the combined legacy suite passed all 16 tests in 0.011 seconds.
- Baseline finding: importing `pipeline.orchestrator` in the project virtual
  environment currently fails because eager job discovery imports MinIO while
  the installed environment lacks the declared `minio` package. This must be
  surfaced by RQ-004 dependency/import checks and eliminated by RQ-012.

Next action: add repeatable quality-gate commands for isolated tests, Django
checks, import smoke checks, migration drift, and forbidden legacy imports.

### 2026-08-04 — RQ-004 repeatable quality gates

- Added `make test-unit`, `make check-refactor`, and `make check-refactor-full`.
- The offline gate parses repository Python, checks merge markers, and runs all
  infrastructure-free characterization tests.
- The full gate additionally runs Django checks, migration drift detection, and
  an orchestrator import smoke test.
- Corrected the stale `make test` app list (`articles` no longer exists).
- Verification: `.venv/bin/python scripts/refactor_quality_gate.py` parsed 114
  Python files and passed all 16 characterization tests.
- Environment finding: `uv sync --frozen` requires explicit approval before the
  full gate can install the already-locked MinIO dependency. The full gate remains
  pending and is not treated as passed.

Next action: run and commit the offline gate, then obtain dependency-sync approval
and pass the full Release Gate 1 checks before RQ-005.

## Completion evidence

- RQ-001: proven by commit `54a6290` and the three accepted ADRs.
- RQ-002: proven by commit `ac96db0`; nine isolated tests pass.
- RQ-003: proven by commit `dad57f5`; combined suite passes 16 tests.
- RQ-004: quality-gate script and Make targets; commit pending.
