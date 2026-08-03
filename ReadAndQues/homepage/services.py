from pipeline.etl.registry import get_pipe
from database.Mongo.crud import get_paraphrase_demo

def get_hot_news():
    # We can fetch completed articles for Hot News. Limit to top 6.
    completed_result = get_pipe("get_completed_articles_pipe").invoke(limit=6)
    return completed_result.get("context", {}).get("articles_list", [])

def get_recommendations(user):
    # TODO: In the future, this can be personalized. 
    # For now, return some latest completed articles or a subset.
    completed_result = get_pipe("get_completed_articles_pipe").invoke(limit=4)
    return completed_result.get("context", {}).get("articles_list", [])

def get_daily_vocab():
    # Placeholder for daily vocab.
    return {
        "word": "Serendipity",
        "type": "noun",
        "meaning": "The occurrence and development of events by chance in a happy or beneficial way.",
        "example": "A fortunate stroke of serendipity."
    }

def get_explore_tests(theme=None, genre=None, page=1, limit=12):
    completed_result = get_pipe("get_completed_articles_pipe").invoke(
        theme=theme if theme != "All" else None,
        genre=genre if genre != "All" else None,
        limit=limit * page # simple logic for now, or just limit=100 and paginate in view
    )
    return completed_result.get("context", {}).get("articles_list", [])

def get_user_attempted_ids(user_id):
    if not user_id:
        return set()
    attempt_result = get_pipe("get_user_attempted_ids_pipe").invoke(user_id=user_id)
    return attempt_result.get("context", {}).get("attempted_ids", set())

def get_demo_paraphrase():
    return get_paraphrase_demo()
