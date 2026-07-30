from pipeline.ai_core.graphs.question_generator.schemas import ThemeCategory
from database.Mongo.connection import article_collection
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
            # Get 3 most recently created articles as "trending" for now.
            # In a real scenario, this could be based on views or stars.
            cursor = article_collection.find(
                {"status": "completed"}, 
                {"title": 1, "_id": 1}
            ).sort("created_at", -1).limit(3)
            
            trending_topics = [
                {"id": str(doc["_id"]), "title": doc.get("title", "No Title")}
                for doc in cursor
            ]
            
            # Cache for 15 minutes
            cache.set("global_trending_topics", trending_topics, 60 * 15)
        except Exception:
            trending_topics = []

    return {
        "nav_themes": themes,
        "trending_topics": trending_topics,
    }
