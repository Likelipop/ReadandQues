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
            db["article_index"].create_index("url", unique=True, name="url_unique")
            db["article_index"].create_index("stage", name="stage_1")
            db["article_index"].create_index("ai_status", name="ai_status_1")
            db["article_index"].create_index([("published_at", -1)], name="published_at_desc")

            db["exams"].create_index("article_id", unique=True, name="article_id_unique")
            db["exams"].create_index([("theme", 1), ("genre", 1)], name="theme_genre")

            db["attempts"].create_index([("user_id", 1), ("article_id", 1)], name="user_article")
            db["reading_history"].create_index([("user_id", 1), ("article_id", 1)], unique=True, name="user_article_unique")
            db["user_highlights"].create_index([("user_id", 1), ("article_id", 1)], name="user_article_highlights")
            db["rss_links"].create_index([("link", 1), ("pubDate", 1)], unique=True, name="rss_link_pubdate_unique")

            self.stdout.write(self.style.SUCCESS("✅ MongoDB indexes created successfully."))
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
