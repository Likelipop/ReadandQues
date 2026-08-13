"""
service/orchestration/pipes.py — Centralized Pipeline Declarations.

Zen design: All pipelines (batch, single article, AI-only) are composed
by chaining pure atomic jobs. Zero monolithic script jobs.
"""

import service.orchestration.jobs  # noqa: F401
from service.orchestration.configuration import Pipe

# ── 1. System Maintenance ─────────────────────────────────────────────────────
init_pipe = Pipe("init_pipe").add_job("init_db")

# ── 2. Medallion Batch Data Pipelines ─────────────────────────────────────────
ingest_bronze_pipe = (
    Pipe("ingest_bronze_pipe")
    .add_job("read_rss_sources")
    .add_job("fetch_rss_links")
    .add_job("filter_new_links")
    .add_job("ingest_to_bronze")
)

bronze_to_silver_pipe = (
    Pipe("bronze_to_silver_pipe")
    .add_job("fetch_unprocessed_bronze")
    .add_job("extract_bronze")
    .add_job("validate_and_clean")
    .add_job("save_to_silver")
)

silver_to_gold_pipe = (
    Pipe("silver_to_gold_pipe")
    .add_job("fetch_unprocessed_silver")
    .add_job("run_ai_enrichment")
    .add_job("save_to_gold")
)

# ── 3. On-Demand Single Article Pipeline ──────────────────────────────────────
# Composed entirely by chaining atomic jobs: crawl → validate/clean → save silver → AI → save gold
single_article_pipe = (
    Pipe("single_article_pipe")
    .add_job("ingest_single_to_bronze")
    .add_job("validate_and_clean")
    .add_job("save_to_silver")
    .add_job("run_ai_enrichment")
    .add_job("save_to_gold")
)

# ── 4. On-Demand AI-Only Re-run Pipeline ──────────────────────────────────────
# Re-runs AI enrichment for an existing silver article
ai_only_pipe = (
    Pipe("ai_only_pipe")
    .add_job("fetch_single_silver")
    .add_job("run_ai_enrichment")
    .add_job("save_to_gold")
)

# ── 5. Smart Ink Paraphrase Pipeline ──────────────────────────────────────────
smart_ink_pipe = (
    Pipe("smart_ink_pipe")
    .add_job("find_cached_paraphrase")
    .add_job("run_paraphrase_llm")
    .add_job("save_paraphrase")
)
