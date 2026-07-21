import os
import sys
from pathlib import Path
from bson import ObjectId

_PROJECT_ROOT = Path(__file__).resolve().parent / "ReadAndQues"
sys.path.insert(0, str(_PROJECT_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ReadAndQues.settings")
import django
django.setup()

from articles.utils.db import article_collection
from articles.models import ArticleMongoModel
from pydantic import ValidationError

doc = article_collection.find_one({"_id": ObjectId("6a5dd419a0753f1b43370140")})
doc["_id"] = str(doc["_id"])

try:
    article = ArticleMongoModel.model_validate(doc)
    print("VALIDATION SUCCESS")
except ValidationError as e:
    print("VALIDATION FAILED:", e)

