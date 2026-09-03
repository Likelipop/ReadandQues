"""
NewsPipeline/jobs.py — Asset jobs and schedules for daily news ingestion and processing.
"""

from dagster import AssetSelection, build_schedule_from_partitioned_job, define_asset_job, in_process_executor

# 1. Daily News Pipeline Job: Processes daily assets from Bronze to Gold
# Uses in_process_executor to prevent concurrent child process memory spikes (SIGKILL)
daily_news_job = define_asset_job(
    name="daily_news_job",
    selection=AssetSelection.assets(
        "bronze_links",
        "silver_raw_html",
        "silver_cleaned_articles",
        "gold_content",
        "gold_semantic_chunks",
    ),
    executor_def=in_process_executor,
    description="Daily partitioned pipeline: RSS Ingestion -> HTML download -> Clean text -> Semantic chunks.",
)

# 2. Automated Daily Schedule: Triggers the daily partition run at the end of each day
daily_news_schedule = build_schedule_from_partitioned_job(
    job=daily_news_job,
    name="daily_news_schedule",
    description="Automated daily schedule for news ingestion and processing.",
)

# 3. Standalone Reindexing & Keyword Extraction Job: Unpartitioned full corpus BM25 build & keyword upsert
reindex_job = define_asset_job(
    name="reindex_job",
    selection=AssetSelection.assets("gold_bm25_index", "gold_article_keywords"),
    executor_def=in_process_executor,
    description="Corpus-level job: scan all gold articles, upload BM25 pickle index to MinIO, and extract keywords.",
)
