from django.core.management.base import BaseCommand
import service.infrastructure.bm25.connection as bm25_conn


class Command(BaseCommand):
    help = "Rebuild in-memory BM25 index from article_index."

    def handle(self, *args, **options):
        self.stdout.write("Rebuilding BM25 index...")
        bm25_conn.rebuild_index()
        self.stdout.write(self.style.SUCCESS("BM25 index rebuilt successfully."))
