from django.views.generic import TemplateView
from django.core.paginator import Paginator
from django.contrib.auth.models import AnonymousUser
import service.orchestration.pipes  # noqa: F401
from .services import (
    get_hot_news, 
    get_recommendations, 
    get_daily_vocab, 
    get_explore_tests, 
    get_user_attempted_ids,
    get_demo_paraphrase,
    update_user_imported_articles_count,
)

class IndexView(TemplateView):
    template_name = "homepage/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        user = getattr(self.request, "user", AnonymousUser())

        # Get themes and genres logic (hardcoded or from constants for now)
        themes = ["All", "Economy", "Society", "Education", "Technology", "Science", "Environment", "Culture", "Health", "General"]
        genres = ["All", "narrative", "poetry", "scientific", "persuasive", "general"]

        selected_theme = self.request.GET.get("theme", "All")
        selected_genre = self.request.GET.get("genre", "All")

        # 1. Hot News
        trending_articles = get_hot_news()

        # 2. Recommendations
        recommended_articles = get_recommendations(user)

        # 3. Daily Vocab
        daily_vocab = get_daily_vocab()

        # 4. Paraphrase Demo
        paraphrase_demo = get_demo_paraphrase()

        # 5. Explore Tests (All Tests replacement)
        all_articles = get_explore_tests(theme=selected_theme, genre=selected_genre, limit=100)
        
        # Mark attempted
        attempted_ids = set()
        if user and getattr(user, "is_authenticated", False):
            attempted_ids = get_user_attempted_ids(getattr(user, "id", None))
            update_user_imported_articles_count(user)

        def mark_attempted(articles):
            valid_articles = []
            for art in articles:
                art_id = str(art.get("article_id") or art.get("id") or art.get("_id") or "").strip()
                if not art_id:
                    continue
                art["id"] = art_id
                art["article_id"] = art_id
                art["has_attempted"] = art_id in attempted_ids
                valid_articles.append(art)
            return valid_articles
            
        trending_articles = mark_attempted(trending_articles)
        recommended_articles = mark_attempted(recommended_articles)
        all_articles = mark_attempted(all_articles)

        # Pagination for explore
        paginator = Paginator(all_articles, 12)
        page_number = self.request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        context.update({
            "trending_articles": trending_articles,
            "recommended_articles": recommended_articles,
            "daily_vocab": daily_vocab,
            "paraphrase_demo": paraphrase_demo,
            "page_obj": page_obj,
            "themes": themes,
            "genres": genres,
            "selected_theme": selected_theme,
            "selected_genre": selected_genre,
        })
        return context
