from django.core.management.base import BaseCommand
import service.infrastructure.mongo.connection as mongo_conn
import service.infrastructure.minio.connection as minio_conn
import service.infrastructure.chroma.connection as chroma_conn
import service.infrastructure.bm25.connection as bm25_conn


class Command(BaseCommand):
    help = "Check connection health for Postgres, MongoDB, MinIO, ChromaDB, and BM25."

    def handle(self, *args, **options):
        self.stdout.write("🔍 Health Check:")

        # MongoDB
        try:
            mongo_conn.get_mongo_client().admin.command("ping")
            self.stdout.write(self.style.SUCCESS("  [OK] MongoDB"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  [FAIL] MongoDB: {e}"))

        # MinIO
        try:
            c = minio_conn.get_minio_client()
            c.list_buckets()
            self.stdout.write(self.style.SUCCESS("  [OK] MinIO"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  [FAIL] MinIO: {e}"))

        # ChromaDB
        try:
            chroma_conn.get_chroma_client()
            self.stdout.write(self.style.SUCCESS("  [OK] ChromaDB"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  [FAIL] ChromaDB: {e}"))

        # BM25
        try:
            bm25_conn.get_index()
            self.stdout.write(self.style.SUCCESS("  [OK] BM25"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  [FAIL] BM25: {e}"))
