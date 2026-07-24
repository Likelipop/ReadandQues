from django.core.management.base import BaseCommand
from pipeline.orchestrator import run_daily_pipeline


class Command(BaseCommand):
    help = "Runs the daily data and AI enrichment pipeline (Silver cleaning & Gold AI generation)."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting daily pipeline execution..."))
        result = run_daily_pipeline()
        self.stdout.write(self.style.SUCCESS(f"Daily pipeline finished: {result['message']}"))
