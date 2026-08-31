"""
NewsPipeline/jobs.py — Asset jobs and schedules for daily news ingestion and processing.
"""

from dagster import AssetSelection, build_schedule_from_partitioned_job, define_asset_job

# 1. Daily News Pipeline Job: Processes daily assets from Bronze to Gold
# Note: Partitioning is automatically inferred from the selected partitioned assets
daily_news_job = define_asset_job(
    name="daily_news_job",
    selection=AssetSelection.assets("bronze_links", "silver_raw_html", "gold_content", "gold_semantic_chunks"),
    description="Daily partitioned pipeline: RSS Ingestion -> HTML download -> Clean text -> Semantic chunks.",
)

# 2. Automated Daily Schedule: Triggers the daily partition run at the end of each day
daily_news_schedule = build_schedule_from_partitioned_job(
    job=daily_news_job,
    name="daily_news_schedule",
    description="Automated daily schedule for news ingestion and processing.",
)

# 3. Standalone Reindexing Job: Unpartitioned full corpus BM25 build
reindex_job = define_asset_job(
    name="reindex_job",
    selection=AssetSelection.assets("gold_bm25_index"),
    description="Corpus-level job: scan all gold articles and upload BM25 pickle index to MinIO.",
)
