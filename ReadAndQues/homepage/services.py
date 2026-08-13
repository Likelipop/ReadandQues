from service.repositories.article_repository import ArticleRepository
from service.repositories.attempt_repository import AttemptRepository


def get_hot_news():
    repo = ArticleRepository()
    articles = repo.list_completed(limit=6)
    return [a.model_dump(mode="json") for a in articles]


def get_recommendations(user):
    repo = ArticleRepository()
    articles = repo.list_completed(limit=4)
    return [a.model_dump(mode="json") for a in articles]


def get_daily_vocab():
    return {
        "word": "Serendipity",
        "type": "noun",
        "meaning": "The occurrence and development of events by chance in a happy or beneficial way.",
        "example": "A fortunate stroke of serendipity."
    }


def get_explore_tests(theme=None, genre=None, page=1, limit=12):
    repo = ArticleRepository()
    filtered_theme = theme if theme != "All" else None
    filtered_genre = genre if genre != "All" else None
    articles = repo.list_completed(theme=filtered_theme, genre=filtered_genre, limit=limit * page)
    return [a.model_dump(mode="json") for a in articles]


def get_user_attempted_ids(user_id):
    if not user_id:
        return set()
    repo = AttemptRepository()
    return repo.get_user_attempted_article_ids(user_id)


def get_demo_paraphrase():
    return {
        "original_summary": "The quick brown fox jumps over the lazy dog in the dense forest.",
        "phrases": [
            {
                "id": "p1",
                "original_text": "quick brown fox",
                "alternatives": ["swift auburn canine", "fast colored fox", "speedy brown fox"]
            }
        ]
    }


def update_user_imported_articles_count(user):
    # Articles are now globally deduplicated, so we track imported count directly on the user profile.
    # We no longer query MongoDB for this.
    try:
        return user.profile.total_articles_imported
    except Exception:
        return 0
