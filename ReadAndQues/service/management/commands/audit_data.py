from django.core.management.base import BaseCommand
from database.Mongo.connection import get_collection
from service.repositories import ArticleRepository


class Command(BaseCommand):
    help = "Audits database records for canonical article_id coverage and validation errors."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting data audit..."))
        repo = ArticleRepository()
        coll = get_collection("article_index")

        total = coll.count_documents({})
        missing_id = coll.count_documents({"_id": {"$exists": False}})

        valid = 0
        invalid = 0

        for doc in coll.find():
            article_id = str(doc.get("_id", ""))
            art = repo.get_by_id(article_id)
            if art:
                valid += 1
            else:
                invalid += 1

        self.stdout.write(self.style.SUCCESS(f"Total article_index records: {total}"))
        self.stdout.write(self.style.SUCCESS(f"Missing explicit _id: {missing_id}"))
        self.stdout.write(self.style.SUCCESS(f"Valid Article models: {valid}"))
        if invalid:
            self.stdout.write(self.style.WARNING(f"Invalid Article models: {invalid}"))
        else:
            self.stdout.write(self.style.SUCCESS("Invalid Article models: 0"))
