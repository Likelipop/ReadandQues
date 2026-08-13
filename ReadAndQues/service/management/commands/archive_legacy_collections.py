import logging
from django.core.management.base import BaseCommand
from database.Mongo.connection import get_mongo_db

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Archives legacy Gold collections to archived_legacy_articles without deleting original collections."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting legacy collections archival..."))
        db = get_mongo_db()
        archive_coll = db["archived_legacy_articles"]

        legacy_names = ["gold_articles", "gold_homepage_articles", "gold_ai_articles"]
        total_archived = 0

        for col_name in legacy_names:
            coll = db[col_name]
            count = coll.count_documents({})
            self.stdout.write(self.style.SUCCESS(f"Archiving collection '{col_name}' ({count} documents)..."))
            for doc in coll.find():
                doc_copy = doc.copy()
                doc_copy["_archived_source_collection"] = col_name
                archive_coll.update_one(
                    {"_id": doc["_id"]},
                    {"$set": doc_copy},
                    upsert=True
                )
                total_archived += 1

        self.stdout.write(self.style.SUCCESS(f"Archival complete. Total archived records: {total_archived}."))
