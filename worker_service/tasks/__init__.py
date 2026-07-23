"""
worker_service/tasks package entrypoint.

Re-exports tasks for easy import compatibility across the project:
`from worker_service.tasks import generate_exam_task, daily_pipeline_task, crawl_paper_task, reindex_bm25_task`
"""

from .ai_exam_tasks import generate_exam_task
from .crawl_tasks import crawl_paper_task
from .pipeline_tasks import daily_pipeline_task, reindex_bm25_task

__all__ = [
    "generate_exam_task",
    "daily_pipeline_task",
    "crawl_paper_task",
    "reindex_bm25_task",
]
