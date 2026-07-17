from django.urls import path
from . import views

urlpatterns = [
    path("import/", views.import_article_view, name="import_article"),
    path("status/<str:pk>/", views.article_status, name="article_status"),
    path("<str:pk>/", views.article_detail, name="article_detail"),
]
