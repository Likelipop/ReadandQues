from django.core.management.base import BaseCommand
from pipeline.orchestrator import run_daily_pipeline


class Command(BaseCommand):
    help = "Runs the daily data and AI enrichment pipeline."

    def add_arguments(self, parser):
        parser.add_argument(
            '--max-news',
            type=int,
            help='Override the default batch size to process a maximum number of news articles.',
        )

    def handle(self, *args, **options):
        max_news = options.get('max_news')
        
        if max_news:
            self.stdout.write(self.style.SUCCESS(f"Starting daily pipeline execution (max_news={max_news})..."))
        else:
            self.stdout.write(self.style.SUCCESS("Starting daily pipeline execution..."))
            
        result = run_daily_pipeline(max_news=max_news)
        self.stdout.write(self.style.SUCCESS(f"Daily pipeline finished: {result['message']}"))
