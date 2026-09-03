"""
NewsPipeline/partitions.py — Daily partition definitions for the pipeline.
"""

import hashlib
import os

from datetime import datetime, timedelta, timezone

from dagster import DailyPartitionsDefinition
from dotenv import find_dotenv, load_dotenv


def get_default_start_date() -> str:
    """Returns the date 30 days prior to current date in YYYY-MM-DD format."""
    past_30_days = datetime.now(timezone.utc) - timedelta(days=30)
    return past_30_days.strftime("%Y-%m-%d")


START_DATE = os.getenv("START_DATE") or get_default_start_date()

# Daily partition definition (1 partition = 1 day, format: 'YYYY-MM-DD')
daily_partitions = DailyPartitionsDefinition(
    start_date=START_DATE,
    timezone="UTC",
)


def url_to_article_id(url: str) -> str:
    """Generate a deterministic 16-character article ID from URL MD5 hash."""
    clean_url = url.strip()
    return f"art_{hashlib.md5(clean_url.encode('utf-8')).hexdigest()[:16]}"


def url_to_partition_key(url: str) -> str:
    """Generate MD5 hex digest of URL."""
    return hashlib.md5(url.strip().encode("utf-8")).hexdigest()
