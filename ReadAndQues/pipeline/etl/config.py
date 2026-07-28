from pathlib import Path

_ETL_DIR = Path(__file__).resolve().parent

# Configs
RSS_FEEDS_FILE = _ETL_DIR / "rss_feeds.txt"
BATCH_SIZE = 10
MAX_INGESTED_NUMBER = 50
MAX_RETRIES = 3
