import sys
import os
from pathlib import Path
import logging

_PROJECT_ROOT = Path(__file__).resolve().parent / "ReadAndQues"
sys.path.insert(0, str(_PROJECT_ROOT))
_WORKSPACE_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_WORKSPACE_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ReadAndQues.settings")
import django
django.setup()

from articles.utils.db import article_collection
from articles.models import ArticleMongoModel
from worker_service.ai_core.chroma_client import articles_collection
from bson import ObjectId

doc = article_collection.find_one({"status": "completed"})
pk = str(doc["_id"])
doc["_id"] = pk
article = ArticleMongoModel.model_validate(doc)

related_articles = []
print("article.analysis exists:", bool(article.analysis))
print("Has core?", hasattr(article.analysis, 'core'))

if hasattr(article.analysis, "core"):
    summary = article.analysis.core.summary
else:
    summary = ""
print("Summary:", summary[:50])

if summary:
    results = articles_collection.query(
        query_texts=[summary],
        n_results=6
    )
    print("IDS:", results['ids'])
    if results and results['ids']:
        related_ids = [str(r_id) for r_id in results['ids'][0] if str(r_id) != str(pk)][:5]
        print("Filtered:", related_ids)
        if related_ids:
            object_ids = [ObjectId(rid) for rid in related_ids]
            cursor = article_collection.find({"_id": {"$in": object_ids}})
            related_docs = {str(d["_id"]): d for d in cursor}
            print("Found in Mongo:", len(related_docs))
            for rid in related_ids:
                if rid in related_docs:
                    r_doc = related_docs[rid]
                    r_doc["id"] = str(r_doc["_id"])
                    related_articles.append(r_doc)

print("FINAL related_articles len:", len(related_articles))
