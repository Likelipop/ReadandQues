# ADR-0002: Application, Orchestration, and Infrastructure Boundaries

Status: accepted

## Decision

The dependency direction is:

```text
Django view
  -> application service
      -> repository for a simple operation
      -> orchestrator for a multi-step workflow
          -> job
              -> domain transformation or repository port
```

- Views handle HTTP validation and responses only.
- Application services implement use cases and authorization boundaries.
- Orchestration coordinates multi-step, retryable work.
- Jobs perform one named unit of business work.
- Repositories hide PyMongo, MinIO, Chroma, and external client details.
- Queries and single writes are not represented as one-job pipelines.
- Infrastructure modules perform no network mutation during import.

## Consequences

The `pipeline` Django app becomes `service`; `etl` becomes `orchestration`.
Existing imports are migrated atomically after characterization coverage exists.
