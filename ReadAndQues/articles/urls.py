from django.urls import path
from . import views

app_name = "articles"

urlpatterns = [
    path("import/", views.import_article, name="import_article"),
    path("status/<str:pk>/", views.article_status, name="article_status"),
    path("api/<str:pk>/smart_paraphrase/", views.smart_paraphrase_view, name="smart_paraphrase"),
    path("api/search/keyword/", views.search_bm25_api, name="search_bm25"),
    path("api/search/semantic/", views.search_semantic_api, name="search_semantic"),
    path("all-tests/", views.all_tests_view, name="all_tests"),
    path("<str:pk>/submit/", views.submit_exam_attempt, name="submit_exam"),
    path("<str:pk>/raw_html/", views.raw_html_view, name="raw_html"),
    path("<str:pk>/", views.article_detail, name="article_detail"),
]
