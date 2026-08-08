from service.ai_core.graphs.question_generator.schemas import ThemeCategory
from service.repositories import ArticleRepository
from django.core.cache import cache

def global_news_context(request):
    """
    Returns context variables for Header and Footer across all pages.
    """
    # 1. Get themes from ThemeCategory enum
    themes = [
        {"id": theme.name, "name": theme.value}
        for theme in ThemeCategory
        if theme.name != "general"
    ]

    # 2. Get trending topics
    # Try to get from cache first to avoid DB hit on every request
    trending_topics = cache.get("global_trending_topics")
    if not trending_topics:
        try:
            repo = ArticleRepository()
            articles = repo.list_completed(limit=3)
            trending_topics = [
                {"id": a.article_id, "title": a.title}
                for a in articles
            ]

            # Cache for 15 minutes
            cache.set("global_trending_topics", trending_topics, 60 * 15)
        except Exception:
            trending_topics = []

    return {
        "nav_themes": themes,
        "trending_topics": trending_topics,
    }
