"""
NewsPipeline/definitions.py — Central Dagster Definitions declaration.
"""

from dagster import Definitions, in_process_executor

from NewsPipeline.assets.bronze import bronze_links
from NewsPipeline.assets.gold import (
    gold_article_keywords,
    gold_bm25_index,
    gold_content,
    gold_semantic_chunks,
)
from NewsPipeline.assets.silver import silver_cleaned_articles, silver_raw_html
from NewsPipeline.jobs import daily_news_job, daily_news_schedule, reindex_job
from NewsPipeline.resources.bm25_resource import BM25Resource
from NewsPipeline.resources.chroma_resource import ChromaResource
from NewsPipeline.resources.minio_io_manager import MinIOIOManager, MinIOResource
from NewsPipeline.resources.mongo_io_manager import MongoIOManager
from NewsPipeline.resources.rss_resource import RSSResource

defs = Definitions(
    assets=[
        bronze_links,
        silver_raw_html,
        silver_cleaned_articles,
        gold_content,
        gold_semantic_chunks,
        gold_bm25_index,
        gold_article_keywords,
    ],
    resources={
        "mongo_io_manager": MongoIOManager(),
        "minio_io_manager": MinIOIOManager(),
        "minio_resource": MinIOResource(),
        "rss_resource": RSSResource(),
        "chroma_resource": ChromaResource(),
        "bm25_resource": BM25Resource(),
    },
    executor=in_process_executor,
    jobs=[
        daily_news_job,
        reindex_job,
    ],
    schedules=[
        daily_news_schedule,
    ],
)
