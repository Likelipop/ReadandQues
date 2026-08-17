from django.urls import path
from . import views

app_name = "readspace"

urlpatterns = [
    # Main Views
    path("all-tests/", views.all_tests_view, name="all_tests"),
    path("import/", views.import_article_view, name="import_article"),
    path("<str:pk>/", views.readspace_view, name="readspace_detail"),

    # AI Quiz & Background generation API
    path("trigger-quiz/<str:pk>/", views.trigger_quiz, name="trigger_quiz"),
    path("status/<str:pk>/", views.article_status, name="article_status"),

    # User submission and tools API
    path("<str:pk>/submit/", views.submit_exam_attempt, name="submit_exam_attempt"),
    path("<str:pk>/proof/<int:idx>/", views.passage_proof_api, name="passage_proof_api"),
    path("api/<str:pk>/smart_paraphrase/", views.smart_paraphrase_api, name="smart_paraphrase"),
    path("api/<str:pk>/save_markers/", views.save_markers_api, name="save_markers"),
    path("api/ai/tool/run/", views.run_ai_tool_api, name="run_ai_tool_api"),
    path("api/ai-tool/", views.run_ai_tool_api, name="run_ai_tool_alias"),

    # Search API
    path("api/search/keyword/", views.search_bm25_api, name="search_bm25_api"),
    path("api/search/semantic/", views.search_semantic_api, name="search_semantic_api"),
]
