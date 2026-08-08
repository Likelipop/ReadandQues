"""
service/repositories/content_repository.py — Article content storage & caching.
Protected by @db_safe error boundary.
"""

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

from database.Minio.connection import init_buckets
from database.Minio.crud import (
    read_bronze_meta,
    read_gold_enriched,
    read_silver_clean,
    save_bronze_html,
    save_bronze_meta,
    save_gold_enriched,
    save_silver_clean,
)
from database.Mongo.crud import find_exact_paraphrase, save_smart_paraphrase
from database.Mongo.homepage_sections import get_section_data, update_section_data
from service.domain.models import RawSourceManifest, Stage
from service.repositories.utils import db_safe

logger = logging.getLogger(__name__)


class ContentRepository:
    """Data access for article content storage (MinIO) and content caching."""

    @staticmethod
    def ensure_buckets() -> None:
        """Ensure MinIO buckets exist."""
        init_buckets()

    # ── Bronze ────────────────────────────────────────────────────────────

    @db_safe(default_return=False)
    def save_bronze_html(self, article_id: str, html_content: str) -> bool:
        return save_bronze_html(article_id, html_content)

    @db_safe(default_return=False)
    def save_bronze_meta(self, article_id: str, meta: Dict[str, Any]) -> bool:
        success = save_bronze_meta(article_id, meta)
        if success:
            try:
                data = json.dumps(meta, ensure_ascii=False, default=str).encode("utf-8")
                sha256_hash = hashlib.sha256(data).hexdigest()
                manifest = RawSourceManifest(
                    article_id=article_id,
                    url=meta.get("url", ""),
                    sha256_hash=sha256_hash,
                    raw_size_bytes=len(data),
                    stage=Stage.BRONZE,
                )
                logger.info(f"Created manifest for {article_id}: {manifest.sha256_hash[:8]}")
            except Exception as me:
                logger.warning(f"Manifest creation skipped for {article_id}: {me}")
        return success

    @db_safe(default_return=None)
    def read_bronze_meta(self, article_id: str) -> Optional[Dict[str, Any]]:
        return read_bronze_meta(article_id)

    # ── Silver ────────────────────────────────────────────────────────────

    @db_safe(default_return=False)
    def save_silver_clean(self, article_id: str, clean_doc: Dict[str, Any]) -> bool:
        return save_silver_clean(article_id, clean_doc)

    @db_safe(default_return=None)
    def read_silver_clean(self, article_id: str) -> Optional[Dict[str, Any]]:
        return read_silver_clean(article_id)

    # ── Gold ──────────────────────────────────────────────────────────────

    @db_safe(default_return=False)
    def save_gold_enriched(self, article_id: str, enriched_doc: Dict[str, Any]) -> bool:
        return save_gold_enriched(article_id, enriched_doc)

    @db_safe(default_return=None)
    def read_gold_enriched(self, article_id: str) -> Optional[Dict[str, Any]]:
        return read_gold_enriched(article_id)

    # ── Text Content ──────────────────────────────────────────────────────

    @db_safe(default_return=None)
    def get_article_text(self, article_id: str) -> Optional[Dict[str, Any]]:
        silver_doc = self.read_silver_clean(article_id)
        if silver_doc:
            return {
                "original_text": silver_doc.get("original_text", ""),
                "cleaned_text": silver_doc.get("original_text", ""),
            }

        bronze_doc = self.read_bronze_meta(article_id)
        if bronze_doc:
            return {
                "original_text": bronze_doc.get("raw_text", ""),
                "cleaned_text": bronze_doc.get("raw_text", ""),
            }

        return None

    # ── Smart Paraphrase Cache ────────────────────────────────────────────

    @db_safe(default_return=None)
    def find_paraphrase(
        self,
        article_id: str,
        paragraph_hash: str,
        start_index: int,
        end_index: int,
    ) -> Optional[Dict]:
        return find_exact_paraphrase(article_id, paragraph_hash, start_index, end_index)

    @db_safe(default_return="")
    def save_paraphrase(self, data: Dict) -> str:
        return save_smart_paraphrase(data)

    # ── Homepage Sections ─────────────────────────────────────────────────

    @db_safe(default_return=False)
    def update_homepage_section(
        self, section_id: str, data: List, expires_hours: int = 24
    ) -> bool:
        return update_section_data(section_id, data, expires_in_hours=expires_hours)

    @db_safe(default_return=None)
    def get_homepage_section(self, section_id: str) -> Optional[List]:
        return get_section_data(section_id)
