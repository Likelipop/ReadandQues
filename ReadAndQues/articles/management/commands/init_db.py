import logging
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth.models import User
import pymongo

from database.Mongo.connection import (
    db, article_collection, reading_history_collection,
    user_highlights_collection, homepage_sections_collection,
    vocab_tracking_collection
)
from database.BM25.connection import rebuild_index

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Initializes the database: runs migrations, creates superuser, creates Mongo indexes, and optionally seeds data."

    def add_arguments(self, parser):
        parser.add_argument(
            '--seed',
            action='store_true',
            help='Seed database with some sample articles',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting DB Initialization..."))

        # 1. Run migrations
        self.stdout.write("Running Django migrations (SQLite)...")
        call_command('migrate', interactive=False)

        # 2. Create Superuser
        self.stdout.write("Checking/Creating superuser...")
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin')
            self.stdout.write(self.style.SUCCESS("Superuser 'admin' with password 'admin' created."))
        else:
            self.stdout.write("Superuser 'admin' already exists.")

        # 3. Create MongoDB Indexes
        self.stdout.write("Creating MongoDB Indexes...")
        try:
            # Articles
            article_collection.create_index([("status", pymongo.ASCENDING)])
            article_collection.create_index([("created_at", pymongo.DESCENDING)])
            article_collection.create_index([("theme", pymongo.ASCENDING)])
            
            # Reading History
            reading_history_collection.create_index([("user_id", pymongo.ASCENDING), ("article_id", pymongo.ASCENDING)], unique=True)
            reading_history_collection.create_index([("last_read_at", pymongo.DESCENDING)])
            
            # Highlights
            user_highlights_collection.create_index([("user_id", pymongo.ASCENDING), ("article_id", pymongo.ASCENDING)])
            
            # Homepage Sections
            homepage_sections_collection.create_index([("section_id", pymongo.ASCENDING)], unique=True)
            homepage_sections_collection.create_index([("expires_at", pymongo.ASCENDING)], expireAfterSeconds=0) # TTL index
            
            # Vocab Tracking
            vocab_tracking_collection.create_index([("user_id", pymongo.ASCENDING), ("word", pymongo.ASCENDING)], unique=True)
            vocab_tracking_collection.create_index([("mastery_level", pymongo.ASCENDING), ("last_reviewed_at", pymongo.ASCENDING)])

            self.stdout.write(self.style.SUCCESS("MongoDB indexes created successfully."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error creating Mongo indexes: {e}"))

        # 4. Rebuild BM25
        self.stdout.write("Rebuilding BM25 Search Index...")
        rebuild_index()

        # 5. Seed data if requested
        if options['seed']:
            self.stdout.write("Seeding sample articles...")
            self.seed_data()
        
        self.stdout.write(self.style.SUCCESS("Database Initialization Completed!"))

    def seed_data(self):
        from pipeline.etl.jobs.single_article import process_single_article
        
        sample_urls = [
            "https://www.bbc.com/news/articles/cdx02xjeepko",
            "https://vnexpress.net/thu-tuong-chi-dao-kiem-soat-lam-phat-nam-2024-4763138.html"
        ]
        
        for idx, url in enumerate(sample_urls):
            self.stdout.write(f"Seeding article {idx+1}/{len(sample_urls)}: {url}")
            try:
                # Use a fake object ID for seed
                article_id = f"seed_art_{idx}"
                result = process_single_article(article_id=article_id, url=url)
                if result.get("status") == "completed":
                    self.stdout.write(self.style.SUCCESS(f"Successfully seeded: {url}"))
                else:
                    self.stdout.write(self.style.WARNING(f"Seed failed for {url}: {result.get('error')}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error seeding {url}: {e}"))
