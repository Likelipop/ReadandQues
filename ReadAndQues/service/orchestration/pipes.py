# Ensure all jobs are loaded
import service.orchestration.jobs  # noqa: F401
from service.orchestration.configuration import Pipe

# 1. System Maintenance
init_pipe = Pipe("init_pipe").add_job("init_db")

# 2. Medallion Data Pipelines
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

# 3. On-Demand Pipelines
single_article_pipe = Pipe("single_article_pipe").add_job("process_single_article")

smart_ink_pipe = (
    Pipe("smart_ink_pipe")
    .add_job("find_cached_paraphrase")
    .add_job("run_paraphrase_llm")
    .add_job("save_paraphrase")
)
