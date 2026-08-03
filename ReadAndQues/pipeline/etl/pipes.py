# Ensure all jobs are loaded
import pipeline.etl.jobs  # noqa: F401
from pipeline.etl.pipeline import Pipe

# 6.1 init_pipe
init_pipe = Pipe("init_pipe").add_job("init_db")

# 6.2 Medallion: Bronze Ingestion Pipe (RSS -> MinIO)
ingest_bronze_pipe = (
    Pipe("ingest_bronze_pipe")
    .add_job("read_rss_sources")
    .add_job("fetch_rss_links")
    .add_job("filter_new_links")
    .add_job("ingest_to_bronze")
)

# 6.3 Medallion: Bronze to Silver Pipe (MinIO -> MinIO + Mongo Tracker)
bronze_to_silver_pipe = (
    Pipe("bronze_to_silver_pipe")
    .add_job("fetch_unprocessed_bronze")
    .add_job("extract_html_content")
    .add_job("validate_articles")
    .add_job("clean_article_text")
    .add_job("save_to_silver")
)

# 6.4 Medallion: Silver to Gold Pipe (MinIO -> Mongo Gold Collections)
silver_to_gold_pipe = (
    Pipe("silver_to_gold_pipe")
    .add_job("fetch_unprocessed_silver")
    .add_job("transform_for_homepage")
    .add_job("transform_for_ai")
    .add_job("save_to_gold_mongo")
)

# 6.5 AI features and single article pipes (existing)
generate_questions_pipe = Pipe("generate_questions_pipe").add_job("generate_questions")
generate_paraphrase_pipe = Pipe("generate_paraphrase_pipe").add_job("generate_paraphrase")
single_article_pipe = Pipe("single_article_pipe").add_job("process_single_article")

# Query pipes
related_articles_pipe = Pipe("related_articles_pipe").add_job("fetch_related_articles")
get_article_by_id_pipe = Pipe("get_article_by_id_pipe").add_job("db_get_article_by_id")
get_completed_articles_pipe = Pipe("get_completed_articles_pipe").add_job("db_get_completed_articles")
get_user_attempted_ids_pipe = Pipe("get_user_attempted_ids_pipe").add_job("db_get_user_attempted_ids")

# Action pipes
save_exam_attempt_pipe = Pipe("save_exam_attempt_pipe").add_job("db_save_exam_attempt")

# Smart Ink Paraphrase pipe
smart_ink_pipe = (
    Pipe("smart_ink_pipe")
    .add_job("db_find_overlapping_paraphrase")
    .add_job("logic_smart_paraphrase_llm")
    .add_job("db_save_smart_paraphrase")
)

find_related_by_markers_pipe = Pipe("find_related_by_markers_pipe").add_job("db_find_related_by_markers")
