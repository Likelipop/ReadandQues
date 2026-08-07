from django.core.management.base import BaseCommand
from database.Mongo.connection import article_collection
from service.repositories.article_repository import ArticleRepository


class Command(BaseCommand):
    help = "Audits database records for canonical article_id coverage and validation errors."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting data audit..."))
        repo = ArticleRepository()

        total = article_collection.count_documents({})
        missing_id = article_collection.count_documents({"article_id": {"$exists": False}})

        valid_contracts = 0
        invalid_contracts = 0

        for doc in article_collection.find():
            try:
                repo.adapter.to_contract(doc)
                valid_contracts += 1
            except Exception:
                invalid_contracts += 1

        self.stdout.write(self.style.SUCCESS(f"Total Mongo articles: {total}"))
        self.stdout.write(self.style.SUCCESS(f"Missing explicit article_id: {missing_id}"))
        self.stdout.write(self.style.SUCCESS(f"Valid canonical contracts: {valid_contracts}"))
        if invalid_contracts:
            self.stdout.write(self.style.WARNING(f"Invalid contracts: {invalid_contracts}"))
        else:
            self.stdout.write(self.style.SUCCESS("Invalid contracts: 0"))
