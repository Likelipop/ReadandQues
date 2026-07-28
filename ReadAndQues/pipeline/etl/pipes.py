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
    .add_job("clean_text")
)

# 6.3 generate_questions_pipe (AI graph)
generate_questions_pipe = Pipe("generate_questions_pipe").add_job("generate_questions")

# 6.4 generate_paraphrase_pipe (AI paraphrase)
generate_paraphrase_pipe = Pipe("generate_paraphrase_pipe").add_job("generate_paraphrase")
