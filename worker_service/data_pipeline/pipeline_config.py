"""
worker_service/data_pipeline/pipeline_config.py — Pipeline configuration.

Central configuration for the Bronze → Silver → Gold data pipeline.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

# ── MongoDB Connection ──────────────────────────────────────────────────────
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://admin:changeme@localhost:27017/articlesDB?authSource=admin",
)
DB_NAME = os.getenv("MONGO_DB_NAME", "articles")

# ── Collection Names ────────────────────────────────────────────────────────
BRONZE_COLLECTION = "bronze_articles"
SILVER_COLLECTION = "silver_articles"
GOLD_COLLECTION = "gold_articles"
LOGS_COLLECTION = "pipeline_logs"
ATTEMPTS_COLLECTION = "attempts"

# ── Pipeline Settings ───────────────────────────────────────────────────────
MAX_INGESTED_NUMBER = int(os.getenv("MAX_INGESTED_NUMBER", "20"))
CRON_SCHEDULE = os.getenv("PIPELINE_CRON", "0 0 * * *")  # every day

# ── Bronze Stage ────────────────────────────────────────────────────────────
BATCH_SIZE = int(os.getenv("PIPELINE_BATCH_SIZE", "20"))
MIN_ARTICLE_WORD_COUNT = 100  # skip articles shorter than this

# ── Silver Stage ────────────────────────────────────────────────────────────
SILVER_MIN_WORD_COUNT = 150
SILVER_MAX_WORD_COUNT = 50000  # reject suspiciously long articles

# ── RSS Feeds file ──────────────────────────────────────────────────────────
RSS_FEEDS_FILE = Path(__file__).resolve().parent / "rss_feeds.txt"
