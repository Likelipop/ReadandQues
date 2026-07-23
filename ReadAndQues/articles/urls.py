from django.urls import path

from . import views

# Đặt app_name để sử dụng tính năng đảo ngược URL (reverse URL) trong view/template
app_name = "articles"

urlpatterns = [
    # Đường dẫn trang dán link cào báo: tên_miền.com/articles/import/
    path("import/", views.import_article, name="import_article"),
    # Đường dẫn kiểm tra trạng thái xử lý bài báo
    path("status/<str:pk>/", views.article_status, name="article_status"),
    # API nhận kết quả nộp bài thi và trả về bài báo liên quan
    path("<str:pk>/submit/", views.submit_exam_attempt, name="submit_exam"),
    # Đường dẫn lấy raw HTML để nhúng vào Iframe
    path("<str:pk>/raw_html/", views.raw_html_view, name="raw_html"),
    # Đường dẫn trang chi tiết bài báo (nhận chuỗi ObjectId từ MongoDB)
    path("<str:pk>/", views.article_detail, name="article_detail"),
    # Đường dẫn trang danh sách toàn bộ bài báo đã xử lý thành công
    path("all-tests", views.all_tests_view, name="all_tests"),
]
