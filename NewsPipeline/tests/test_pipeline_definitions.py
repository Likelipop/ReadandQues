"""
NewsPipeline/tests/test_pipeline_definitions.py — Unit tests for Dagster definitions, daily partitions, assets, and resources.
"""

from NewsPipeline.definitions import defs
from NewsPipeline.partitions import daily_partitions, url_to_article_id, url_to_partition_key
from NewsPipeline.resources.rss_resource import _parse_entry_datetime


def test_definitions_load_cleanly():
    """Verify that all 6 Medallion assets load properly with expected naming convention."""
    asset_keys = [a.key.to_user_string() for a in defs.assets]

    assert "bronze_links" in asset_keys
    assert "silver_raw_html" in asset_keys
    assert "silver_cleaned_articles" in asset_keys
    assert "gold_content" in asset_keys
    assert "gold_semantic_chunks" in asset_keys
    assert "gold_bm25_index" in asset_keys
    assert "gold_article_keywords" in asset_keys


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


def test_sanitize_article_text():
    """Verify that sanitize_article_text strips leading metadata, trailing footers, and normalizes headings."""
    from NewsPipeline.assets.silver import sanitize_article_text

    raw_sample = (
        "- Date:\n"
        "- August 29, 2026\n"
        "- Source:\n"
        "- University News\n"
        "- Summary:\n"
        "- Brief summary text.\n"
        "- Share:\n"
        "This is the first real paragraph of the news article.\n\n"
        "**Subheading Section**\n"
        "This is the second paragraph describing research in detail.\n\n"
        "**Story Source:**\n"
        "Materials provided by University. Note: Content edited.\n"
        "**Journal Reference:**\n"
        "1. Author et al. Paper title.\n"
        "**Cite This Page:**\n"
        "ScienceDaily 2026."
    )

    cleaned = sanitize_article_text(raw_sample)

    # Asserts leading metadata stripped
    assert "- Date:" not in cleaned
    assert "- Source:" not in cleaned
    assert "- Share:" not in cleaned
    # Asserts body kept
    assert "This is the first real paragraph of the news article." in cleaned
    # Asserts heading normalized
    assert "### Subheading Section" in cleaned
    assert "This is the second paragraph describing research in detail." in cleaned
    # Asserts footer stripped
    assert "Story Source:" not in cleaned
    assert "Journal Reference:" not in cleaned
    assert "Cite This Page:" not in cleaned


def test_extract_keywords_from_bm25():
    """Verify that extract_keywords_from_bm25 produces 1 to 2 capitalized keywords using TF*IDF."""
    from NewsPipeline.assets.gold import extract_keywords_from_bm25
    from NewsPipeline.resources.bm25_resource import BM25Resource

    bm25_res = BM25Resource()

    class MockBM25Index:
        idf = {
            "quantum": 4.5,
            "computing": 3.8,
            "algorithm": 2.0,
            "research": 0.5,
        }

    title = "Quantum Computing Breakthrough in Superconducting Qubits"
    text = (
        "Researchers have achieved quantum supremacy with a new quantum processor. "
        "The quantum algorithm operates with ultra-low decoherence rates in computing tests."
    )

    kws = extract_keywords_from_bm25(title, text, MockBM25Index(), bm25_res, max_keywords=2)
    assert len(kws) in (1, 2)
    assert "Quantum" in kws
    # All keywords must be capitalized
    for kw in kws:
        assert kw[0].isupper()
