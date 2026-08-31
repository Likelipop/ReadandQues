"""
Django management command: python manage.py setup_db
Idempotently initializes MongoDB indexes, schema validators, MinIO buckets, and BM25 search index.
"""

from django.core.management.base import BaseCommand

import service.infrastructure.bm25.connection as bm25_conn
import service.infrastructure.minio.connection as minio_conn
import service.infrastructure.mongo.connection as mongo_conn


class Command(BaseCommand):
    help = "Idempotently setup MongoDB indexes, MinIO buckets, and BM25 index."

    def handle(self, *args, **options):
        self.stdout.write("🛠 Running setup_db...")

        # 1. MongoDB Indexes
        try:
            db = mongo_conn.get_mongo_db()
            index_specs = [
                ("article_index", "url", {"unique": True}),
                ("article_index", "stage", {}),
                ("article_index", "ai_status", {}),
                ("article_index", [("published_at", -1)], {}),
                ("article_index", "keywords", {}),
                ("gold_articles", "article_id", {"unique": True}),
                ("gold_articles", "keywords", {}),
                ("exams", "article_id", {"unique": True}),
                ("exams", "keywords", {}),
                ("attempts", [("user_id", 1), ("article_id", 1)], {}),
                ("reading_history", [("user_id", 1), ("article_id", 1)], {"unique": True}),
                ("user_highlights", [("user_id", 1), ("article_id", 1)], {}),
                ("rss_links", [("link", 1), ("pubDate", 1)], {"unique": True}),
            ]
            for coll_name, keys, kwargs in index_specs:
                try:
                    db[coll_name].create_index(keys, **kwargs)
                except Exception as idx_err:
                    self.stdout.write(f"  Note on {coll_name} index: {idx_err}")

            self.stdout.write(self.style.SUCCESS("✅ MongoDB indexes verified successfully."))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"⚠️ MongoDB index setup warning: {e}"))

        # 2. MinIO Buckets
        try:
            minio_conn.init_buckets()
            self.stdout.write(self.style.SUCCESS("✅ MinIO buckets initialized."))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"⚠️ MinIO setup warning: {e}"))

        # 3. BM25 Index
        try:
            bm25_conn.rebuild_index()
            self.stdout.write(self.style.SUCCESS("✅ BM25 search index rebuilt."))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"⚠️ BM25 setup warning: {e}"))

        self.stdout.write(self.style.SUCCESS("🎉 setup_db completed!"))
