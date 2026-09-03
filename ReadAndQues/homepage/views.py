from django.contrib.auth.models import AnonymousUser
from django.core.paginator import Paginator
from django.views.generic import TemplateView

import service.selectors as selectors


class IndexView(TemplateView):
    template_name = "homepage/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = getattr(self.request, "user", AnonymousUser())

        popular_keywords = selectors.get_popular_keywords(limit=10)
        selected_keyword = self.request.GET.get("keyword", "All")

        trending_articles = selectors.get_hot_news(limit=6)
        recommended_articles = selectors.get_recommendations(user=user, limit=4)
        daily_vocab = selectors.get_daily_vocab(user_id=getattr(user, "id", None))

        page_num = self.request.GET.get("page", 1)
        articles_res = selectors.list_completed_articles(
            keyword=selected_keyword, page=int(page_num) if str(page_num).isdigit() else 1, limit=12
        )
        paginator = Paginator(articles_res.get("articles", []), 12)
        page_obj = paginator.get_page(page_num)

        context.update({
            "trending_articles": trending_articles,
            "recommended_articles": recommended_articles,
            "daily_vocab": daily_vocab,
            "page_obj": page_obj,
            "popular_keywords": popular_keywords,
            "selected_keyword": selected_keyword,
        })
        return context
