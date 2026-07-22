from django.urls import path
from . import views

# Đặt app_name để sử dụng tính năng đảo ngược URL (reverse URL) trong view/template
app_name = "articles"

urlpatterns = [
    # Đường dẫn trang dán link cào báo: tên_miền.com/articles/import/
    path("import/", views.import_article, name="import_article"),
    
    # Đường dẫn trang chi tiết bài báo (nhận chuỗi ObjectId từ MongoDB)
    path("<str:pk>/", views.article_detail, name="article_detail"),
]