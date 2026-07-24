"""
pipeline/etl/pipeline_config.py — ETL Pipeline Constants & Configuration.
"""

from pathlib import Path

_ETL_DIR = Path(__file__).resolve().parent

RSS_FEEDS_FILE = _ETL_DIR / "rss_feeds.txt"

BATCH_SIZE = 10
MAX_INGESTED_NUMBER = 50

SILVER_MIN_WORD_COUNT = 150
SILVER_MAX_WORD_COUNT = 15000
