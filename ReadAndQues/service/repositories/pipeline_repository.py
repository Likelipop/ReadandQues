"""
service/repositories/pipeline_repository.py — Data access for the article pipeline.
Protected by @db_safe error boundary.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from database.Mongo.article_index import (
    create_article_index,
    get_article_index,
    get_article_index_by_url,
    list_by_stage,
    list_completed_articles,
    update_ai_status,
    update_article_stage,
    update_article_title,
)
from database.Mongo.crud import (
    batch_insert_rss_links,
    filter_existing_rss_links,
    get_unprocessed_rss_links,
    insert_pipeline_log,
    mark_rss_link_extracted,
)
from database.Mongo.exams import get_exam, get_exams_by_article_ids, save_exam
from service.domain.models import Stage, Status
from service.repositories.utils import db_safe

logger = logging.getLogger(__name__)


class PipelineRepository:
    """Data access for the article ingestion/enrichment pipeline."""

    # ── Article Index Lifecycle ───────────────────────────────────────────

    @db_safe(default_return=False)
    def create_article_index(
        self,
        article_id: str,
        url: str,
        title: str = "",
        source_name: str = "",
        image_url: Optional[str] = None,
        published_at: Optional[datetime] = None,
    ) -> bool:
        return create_article_index(
            article_id=article_id,
            url=url,
            title=title,
            source_name=source_name,
            image_url=image_url,
            published_at=published_at,
            stage=Stage.BRONZE.value,
            ai_status=Status.PENDING.value,
        )

    @db_safe(default_return=None)
    def get_article_index(self, article_id: str) -> Optional[dict]:
        return get_article_index(article_id)

    @db_safe(default_return=None)
    def get_article_index_by_url(self, url: str) -> Optional[dict]:
        return get_article_index_by_url(url)

    @db_safe(default_return=False)
    def update_article_stage(self, article_id: str, stage: Stage) -> bool:
        stage_str = stage.value if hasattr(stage, "value") else str(stage)
        return update_article_stage(article_id, stage_str)

    @db_safe(default_return=False)
    def update_stage(self, article_id: str, stage: Stage) -> bool:
        return self.update_article_stage(article_id, stage)

    @db_safe(default_return=False)
    def update_ai_status(
        self, article_id: str, ai_status: Status, error_message: str = ""
    ) -> bool:
        status_str = ai_status.value if hasattr(ai_status, "value") else str(ai_status)
        return update_ai_status(article_id, status_str, error_message)

    @db_safe(default_return=False)
    def update_article_title(self, article_id: str, title: str) -> bool:
        return update_article_title(article_id, title)

    @db_safe(default_return=[])
    def list_by_stage(self, stage: Stage, limit: int = 50) -> List[dict]:
        stage_str = stage.value if hasattr(stage, "value") else str(stage)
        return list_by_stage(stage_str, limit=limit)

    @db_safe(default_return=[])
    def list_completed(
        self,
        theme: Optional[str] = None,
        genre: Optional[str] = None,
        limit: int = 100,
    ) -> List[dict]:
        return list_completed_articles(limit=limit)

    # ── Exam Persistence ──────────────────────────────────────────────────

    @db_safe(default_return=False)
    def save_exam(self, article_id: str, exam_doc: dict) -> bool:
        return save_exam(article_id, exam_doc)

    @db_safe(default_return=None)
    def get_exam(self, article_id: str) -> Optional[dict]:
        return get_exam(article_id)

    @db_safe(default_return={})
    def get_exams_by_article_ids(self, article_ids: List[str]) -> Dict[str, dict]:
        return get_exams_by_article_ids(article_ids)

    # ── RSS Tracking ──────────────────────────────────────────────────────

    @db_safe(default_return=set())
    def filter_existing_rss_links(self, links: List[str]) -> set:
        return filter_existing_rss_links(links)

    @db_safe(default_return=0)
    def batch_insert_rss_links(self, docs: List[dict]) -> int:
        return batch_insert_rss_links(docs)

    @db_safe(default_return=[])
    def get_unprocessed_rss_links(self, limit: int = 50) -> List[dict]:
        return get_unprocessed_rss_links(limit=limit)

    @db_safe(default_return=False)
    def mark_rss_link_extracted(self, link: str) -> bool:
        return mark_rss_link_extracted(link)

    # ── Pipeline Logs ─────────────────────────────────────────────────────

    @db_safe(default_return="")
    def insert_pipeline_log(
        self,
        stage: str,
        status: str,
        message: str = "",
        document_id: Optional[str] = None,
        url: Optional[str] = None,
    ) -> str:
        return insert_pipeline_log(stage, status, message, document_id, url)

    @db_safe(default_return="")
    def insert_log(
        self,
        stage: str,
        status: str,
        message: str = "",
        document_id: Optional[str] = None,
        url: Optional[str] = None,
    ) -> str:
        return self.insert_pipeline_log(stage, status, message, document_id, url)
