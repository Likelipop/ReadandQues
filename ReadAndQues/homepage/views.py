from django.contrib.auth.models import AnonymousUser
from django.core.paginator import Paginator
from django.views.generic import TemplateView

import service.selectors as selectors


class IndexView(TemplateView):
    template_name = "homepage/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = getattr(self.request, "user", AnonymousUser())

        themes = selectors.get_theme_choices()
        genres = selectors.get_genre_choices()

        selected_theme = self.request.GET.get("theme", "All")
        selected_genre = self.request.GET.get("genre", "All")

        trending_articles = selectors.get_hot_news(limit=6)
        recommended_articles = selectors.get_recommendations(user=user, limit=4)
        daily_vocab = selectors.get_daily_vocab(user_id=getattr(user, "id", None))

        paraphrase_demo = {
            "original": "Climate change poses severe threats to global food security.",
            "paraphrased": "Global food production is gravely endangered by shifts in world climate.",
        }

        all_tests_res = selectors.list_completed_articles(theme=selected_theme, genre=selected_genre, limit=100)
        all_articles = all_tests_res.get("articles", [])

        attempted_ids = set()
        if user and getattr(user, "is_authenticated", False):
            attempted_ids = selectors.get_user_attempted_ids(getattr(user, "id", None))

        def mark_attempted(articles):
            for art in articles:
                aid = str(art.get("article_id") or art.get("id") or "").strip()
                art["has_attempted"] = aid in attempted_ids
            return articles

        trending_articles = mark_attempted(trending_articles)
        recommended_articles = mark_attempted(recommended_articles)
        all_articles = mark_attempted(all_articles)

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
