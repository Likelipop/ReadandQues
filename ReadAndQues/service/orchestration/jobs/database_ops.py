"""
service/orchestration/jobs/database_ops.py — DEPRECATED shim.

All logic has been migrated to maintenance.py and paraphrase.py.
This file remains only to avoid import errors during migration.
Will be removed in Phase 8.
"""

# Re-export from new modules to avoid breaking any remaining references
from service.orchestration.jobs.maintenance import init_db, reindex_search, update_trending  # noqa: F401
from service.orchestration.jobs.paraphrase import (  # noqa: F401
    find_cached_paraphrase,
    run_paraphrase_llm,
    save_paraphrase,
)
