from django.urls import path
from . import views

urlpatterns = [
    path("import/", views.import_article_view, name="import_article"),
    path("status/<str:pk>/", views.article_status, name="article_status"),
    path("all-tests/", views.all_tests_view, name="all_tests"),
    path("<str:pk>/", views.article_detail, name="article_detail"),
    path("<str:pk>/submit/", views.submit_exam_attempt, name="submit_exam_attempt"),
]
