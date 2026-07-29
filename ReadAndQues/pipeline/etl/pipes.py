# Ensure all jobs are loaded
import pipeline.etl.jobs  # noqa: F401
from pipeline.etl.pipeline import Pipe

# 6.1 init_pipe
init_pipe = Pipe("init_pipe").add_job("init_db")

# 6.2 ingest_news_pipe (RSS -> crawl -> clean)
ingest_news_pipe = (
    Pipe("ingest_news_pipe")
    .add_job("extract_rss")
    .add_job("crawl_news")
    .add_job("db_fetch_unprocessed_bronze")
    .add_job("logic_clean_batch")
    .add_job("db_save_silver_batch")
)

# 6.3 generate_questions_pipe (AI graph)
generate_questions_pipe = Pipe("generate_questions_pipe").add_job("generate_questions")

# 6.4 generate_paraphrase_pipe (AI paraphrase)
generate_paraphrase_pipe = Pipe("generate_paraphrase_pipe").add_job("generate_paraphrase")

# Single article real-time pipe
single_article_pipe = Pipe("single_article_pipe").add_job("process_single_article")

# Query pipes
related_articles_pipe = Pipe("related_articles_pipe").add_job("fetch_related_articles")

# Smart Ink Paraphrase pipe
smart_ink_pipe = (
    Pipe("smart_ink_pipe")
    .add_job("db_find_overlapping_paraphrase")
    .add_job("logic_smart_paraphrase_llm")
    .add_job("db_save_smart_paraphrase")
)
