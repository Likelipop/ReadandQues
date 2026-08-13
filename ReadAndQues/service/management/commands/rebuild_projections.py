from django.core.management.base import BaseCommand
from service.repositories import ArticleRepository
from service.repositories.search_repository import SearchRepository


class Command(BaseCommand):
    help = "Rebuilds ChromaDB vector embeddings and BM25 lexical index projections using canonical IDs."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Rebuilding projections..."))
        article_repo = ArticleRepository()
        search_repo = SearchRepository()

        completed_articles = article_repo.list_completed(limit=1000)

        self.stdout.write(self.style.SUCCESS(f"Rebuilding BM25 index from {len(completed_articles)} completed articles..."))
        search_repo.rebuild_keyword_index()

        self.stdout.write(self.style.SUCCESS(f"Rebuilding Chroma vector embeddings..."))
        rebuilt_chroma = 0
        for article in completed_articles:
            if article.summary:
                try:
                    search_repo.index_article_vector(
                        article_id=article.article_id,
                        summary=article.summary,
                        title=article.title,
                        url=article.url,
                        theme=article.theme,
                        genre=article.genre,
                    )
                    rebuilt_chroma += 1
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Could not index vector for {article.article_id}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Projections rebuild complete. Chroma indexed: {rebuilt_chroma}."))
