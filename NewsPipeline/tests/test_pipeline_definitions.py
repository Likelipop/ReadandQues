"""
NewsPipeline/tests/test_pipeline_definitions.py — Unit tests for Dagster definitions, daily partitions, assets, and resources.
"""

from NewsPipeline.definitions import defs
from NewsPipeline.partitions import daily_partitions, url_to_article_id, url_to_partition_key
from NewsPipeline.resources.rss_resource import _parse_entry_datetime


def test_definitions_load_cleanly():
    """Verify that all 5 Medallion assets load properly with expected naming convention."""
    asset_keys = [a.key.to_user_string() for a in defs.assets]

    assert "bronze_links" in asset_keys
    assert "silver_raw_html" in asset_keys
    assert "gold_content" in asset_keys
    assert "gold_semantic_chunks" in asset_keys
    assert "gold_bm25_index" in asset_keys


def test_daily_partitions_configured():
    """Verify daily_partitions configuration and partition format."""
    assert daily_partitions is not None
    assert daily_partitions.timezone == "UTC"


def test_jobs_defined():
    """Verify that daily_news_job and reindex_job are properly configured."""
    job_names = [j.name for j in defs.jobs]

    assert "daily_news_job" in job_names
    assert "reindex_job" in job_names


def test_schedules_defined():
    """Verify that the daily news schedule is configured."""
    schedule_names = [s.name for s in defs.schedules]

    assert "daily_news_schedule" in schedule_names


def test_resources_configured():
    """Verify all 5 required IO Managers and Resources are present."""
    resource_keys = set(defs.resources.keys())

    expected = {
        "mongo_io_manager",
        "minio_io_manager",
        "rss_resource",
        "chroma_resource",
        "bm25_resource",
    }
    assert expected.issubset(resource_keys)


def test_url_article_id_generation():
    """Verify that url_to_article_id produces deterministic art_<hash> IDs."""
    url = "https://example.com/article/1"
    id1 = url_to_article_id(url)
    id2 = url_to_article_id(url)

    assert id1.startswith("art_")
    assert len(id1) == 20  # "art_" + 16 chars
    assert id1 == id2
    assert id1 != url_to_article_id("https://example.com/article/2")


def test_url_partition_key_hashing():
    """Verify that url_to_partition_key produces deterministic 32-character hex MD5 keys."""
    url = "https://example.com/article/1"
    key1 = url_to_partition_key(url)
    key2 = url_to_partition_key(url)

    assert len(key1) == 32
    assert key1 == key2
    assert key1 != url_to_partition_key("https://example.com/article/2")


def test_rss_date_parsing():
    """Verify that _parse_entry_datetime correctly parses time.struct_time to UTC datetime."""
    import time
    fake_entry = {
        "published_parsed": time.strptime("2026-08-30 12:00:00", "%Y-%m-%d %H:%M:%S")
    }
    dt = _parse_entry_datetime(fake_entry)
    assert dt.strftime("%Y-%m-%d") == "2026-08-30"
