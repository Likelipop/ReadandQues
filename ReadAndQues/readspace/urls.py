from django.urls import path
from . import views

app_name = "readspace"

urlpatterns = [
    path("<str:pk>/", views.readspace_view, name="readspace_detail"),
    path("<str:pk>/raw_html/", views.raw_html_view, name="raw_html_view"),
    path("api/<str:pk>/smart_paraphrase/", views.smart_paraphrase_api, name="smart_paraphrase"),
    path("api/<str:pk>/save_markers/", views.save_markers_api, name="save_markers"),
]
