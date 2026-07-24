from django.core.management.base import BaseCommand
from database.BM25.connection import rebuild_index


class Command(BaseCommand):
    help = "Rebuilds the BM25 search index from MongoDB article documents."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Rebuilding BM25 search index..."))
        try:
            rebuild_index()
            self.stdout.write(self.style.SUCCESS("BM25 search index successfully rebuilt."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to rebuild BM25 index: {e}"))
