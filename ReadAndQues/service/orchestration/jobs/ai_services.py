"""
service/orchestration/jobs/ai_services.py
service/orchestration/jobs/database_ops.py

DEPRECATED — These files are kept as backward-compat shims for tests and
any code that still imports from them. All logic has been migrated to:
  - enrichment.py  (AI enrichment jobs)
  - paraphrase.py  (smart paraphrase jobs)
  - maintenance.py (init_db, reindex, trending)

These files will be removed in Phase 8 (final cleanup).
"""

import logging

logger = logging.getLogger(__name__)


def run_ai_pipeline(text: str) -> dict | None:
    """Backward-compat shim. Use enrichment._run_question_generator() instead."""
    from service.orchestration.jobs.enrichment import _run_question_generator
    return _run_question_generator(text)
