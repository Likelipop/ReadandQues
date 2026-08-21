from django.urls import path

from . import views
from .api import api as readspace_api

app_name = "readspace"

urlpatterns = [
    # ── HTML Page Views ──────────────────────────────────────────────────────
    path("all-tests/", views.all_tests_view, name="all_tests"),
    path("import/", views.import_article_view, name="import_article"),
    path("<str:pk>/", views.readspace_view, name="readspace_detail"),

    # ── AI Quiz & Status ─────────────────────────────────────────────────────
    path("trigger-quiz/<str:pk>/", views.trigger_quiz, name="trigger_quiz"),
    path("status/<str:pk>/", views.article_status, name="article_status"),

    # ── Interactive Practice & Workspace Tools ───────────────────────────────
    path("<str:pk>/submit/", views.submit_exam_attempt, name="submit_exam_attempt"),
    path("<str:pk>/proof/<int:idx>/", views.passage_proof_api, name="passage_proof_api"),
    path("api/<str:pk>/smart_paraphrase/", views.smart_paraphrase_api, name="smart_paraphrase"),
    path("api/<str:pk>/save_markers/", views.save_markers_api, name="save_markers"),
    path("api/ai/tool/run/", views.run_ai_tool_api, name="run_ai_tool_api"),

    # ── Streaming & Search ───────────────────────────────────────────────────
    path("api/rag/stream/", views.rag_stream_api, name="rag_stream_api"),
    path("api/explain/stream/", views.explain_stream_api, name="explain_stream_api"),
    path("api/<str:pk>/explain/stream/", views.explain_stream_api, name="explain_stream_api_pk"),
    path("api/search/keyword/", views.search_bm25_api, name="search_bm25_api"),
    path("api/search/semantic/", views.search_semantic_api, name="search_semantic_api"),
]
