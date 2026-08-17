from django.core.management.base import BaseCommand
import service.services as services


class Command(BaseCommand):
    help = "Run daily news ingestion and enrichment pipeline."

    def add_arguments(self, parser):
        parser.add_argument("--max-news", type=int, default=10, help="Max news articles to crawl")

    def handle(self, *args, **options):
        max_news = options.get("max_news", 10)
        self.stdout.write(f"Starting daily pipeline (max_news={max_news})...")
        res = services.run_daily_ingestion(max_articles=max_news)
        self.stdout.write(self.style.SUCCESS(f"Daily pipeline completed: {res}"))
