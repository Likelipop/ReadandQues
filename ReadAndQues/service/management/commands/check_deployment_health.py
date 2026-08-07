from django.core.management.base import BaseCommand
from django.db import connection
from database.Mongo.connection import get_mongo_client, get_mongo_db
from database.Minio.connection import client as minio_client, BRONZE_BUCKET, SILVER_BUCKET
from database.BM25.connection import get_index
from database.Chroma.connection import get_chroma_client


class Command(BaseCommand):
    help = "Verifies health and readiness of PostgreSQL, MongoDB, MinIO, BM25, and ChromaDB."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("=== Deployment Health Check ==="))
        all_ok = True

        # 1. PostgreSQL Check
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            self.stdout.write(self.style.SUCCESS("[OK] PostgreSQL database connection."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"[FAIL] PostgreSQL database connection failed: {e}"))
            all_ok = False

        # 2. MongoDB Check
        try:
            db = get_mongo_db()
            db.command("ping")
            self.stdout.write(self.style.SUCCESS("[OK] MongoDB database ping."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"[WARN] MongoDB database offline or unreachable: {e}"))

        # 3. MinIO Check
        try:
            exists = minio_client.bucket_exists(BRONZE_BUCKET)
            self.stdout.write(self.style.SUCCESS(f"[OK] MinIO client (Bronze bucket exists: {exists})."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"[WARN] MinIO service unreachable: {e}"))

        # 4. BM25 Index Check
        try:
            idx, corpus_ids = get_index()
            self.stdout.write(self.style.SUCCESS(f"[OK] BM25 lexical index (corpus size: {len(corpus_ids)})."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"[WARN] BM25 index unavailable: {e}"))

        # 5. ChromaDB Check
        try:
            c, col = get_chroma_client()
            if c:
                self.stdout.write(self.style.SUCCESS("[OK] ChromaDB vector store connected."))
            else:
                self.stderr.write(self.style.ERROR("[WARN] ChromaDB vector store disconnected."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"[WARN] ChromaDB error: {e}"))

        if all_ok:
            self.stdout.write(self.style.SUCCESS("=== Health Check PASS ==="))
        else:
            self.stderr.write(self.style.ERROR("=== Health Check WARNING/FAIL ==="))
            raise SystemExit(1)
