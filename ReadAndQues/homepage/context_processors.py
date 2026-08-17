from service.domain.enums import ThemeCategory
import service.selectors as selectors
from django.core.cache import cache


def global_news_context(request):
    """Returns context variables for Header and Footer across all pages."""
    themes = [
        {"id": theme.name, "name": theme.value}
        for theme in ThemeCategory
        if theme.name != "GENERAL"
    ]

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
        "nav_themes": themes,
        "trending_topics": trending_topics,
    }
