from pathlib import Path

_ORCHESTRATION_DIR = Path(__file__).resolve().parent.parent

# Configs
RSS_FEEDS_FILE = _ORCHESTRATION_DIR / "rss_feeds.txt"
BATCH_SIZE = 10
MAX_INGESTED_NUMBER = 50
MAX_RETRIES = 3
