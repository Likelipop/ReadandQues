from django.core.cache import cache

import service.selectors as selectors
from shared.enums import ThemeCategory


def global_news_context(request):
    """Returns context variables for Header and Footer across all pages."""
    keywords = selectors.get_popular_keywords(limit=6)

    trending_topics = cache.get("global_trending_topics")
    if not trending_topics:
        try:
            articles = selectors.get_hot_news(limit=3)
            trending_topics = [
                {"id": a.get("article_id") or a.get("id"), "title": a.get("title")}
                for a in articles
            ]
            cache.set("global_trending_topics", trending_topics, 60 * 15)
        except Exception:
            trending_topics = []

    return {
        "nav_keywords": keywords,
        "trending_topics": trending_topics,
    }
