import sys
from pathlib import Path
import logging

_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ReadAndQues.articles.utils.db import article_collection
from ReadAndQues.articles.models import ArticleMongoModel

doc = article_collection.find_one({"status": "completed"})
article = ArticleMongoModel.model_validate(doc)
print(type(article.analysis))
try:
    summary = article.analysis.get("core", {}).get("summary", "")
    print(summary)
except Exception as e:
    print("ERROR:", type(e), e)
