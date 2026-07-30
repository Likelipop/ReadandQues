# 🐛 Bug Report: `TemplateDoesNotExist: homepage/index.html` trên Production (Docker)

## Triệu chứng (Symptoms)
Sau khi `docker compose up`, Gunicorn khởi động bình thường nhưng **mọi request đến `/` đều trả về HTTP 500** với lỗi:
```
django.template.exceptions.TemplateDoesNotExist: homepage/index.html
```
Lỗi này lặp lại liên tục (mỗi ~10 giây do healthcheck GET `/`).

---

## Nguyên nhân gốc (Root Cause)
Docker container sử dụng biến môi trường:
```yaml
DJANGO_SETTINGS_MODULE: ReadAndQues.settings_prod
```
File `settings_prod.py` được viết **trước khi các Task 1-5 được triển khai**, nên nó bị **thiếu đồng bộ (out-of-sync)** so với `settings.py` (dùng khi dev local).

Cụ thể, `settings_prod.py` có **3 vấn đề lớn**:

### 1. Thiếu `homepage` và `readspace` trong `INSTALLED_APPS`
```python
# settings_prod.py (HIỆN TẠI - SAI)
INSTALLED_APPS = [
    ...
    "accounts",
    "articles",
    "pipeline",
    # ← THIẾU "homepage"
    # ← THIẾU "readspace"
]
```
Khi `APP_DIRS = True`, Django chỉ quét thư mục `templates/` trong các app được liệt kê ở `INSTALLED_APPS`. Vì `homepage` không có mặt → Django không tìm thấy `homepage/templates/homepage/index.html`.

### 2. Thiếu Context Processor `global_news_context`
```python
# settings_prod.py (HIỆN TẠI - SAI)
"context_processors": [
    "django.template.context_processors.request",
    "django.contrib.auth.context_processors.auth",
    "django.contrib.messages.context_processors.messages",
    # ← THIẾU "articles.context_processors.global_news_context"
],
```
Ngay cả khi fix INSTALLED_APPS, template `base.html` vẫn sẽ crash vì biến `nav_themes` và `trending_topics` không được inject.

### 3. `DIRS` hardcode thư mục `articles/templates`
```python
"DIRS": [BASE_DIR / "articles" / "templates"],
```
Đây không phải là lỗi gây crash, nhưng là một thiết kế thừa. Khi `APP_DIRS = True`, Django đã tự động quét `templates/` trong mỗi app. Việc hardcode thêm `DIRS` chỉ cần thiết nếu có template nằm ngoài app.

---

## Hướng giải quyết (Fix)
Đồng bộ `settings_prod.py` với `settings.py` ở 3 điểm trên:

### Sửa 1: Thêm `homepage` và `readspace` vào `INSTALLED_APPS`
```diff
 INSTALLED_APPS = [
     ...
     "accounts",
     "articles",
     "pipeline",
+    "homepage",
+    "readspace",
 ]
```

### Sửa 2: Thêm Context Processor
```diff
 "context_processors": [
     "django.template.context_processors.request",
     "django.contrib.auth.context_processors.auth",
     "django.contrib.messages.context_processors.messages",
+    "articles.context_processors.global_news_context",
 ],
```

### Sửa 3: (Tùy chọn) Dọn `DIRS`
```diff
-"DIRS": [BASE_DIR / "articles" / "templates"],
+"DIRS": [],
```

---

## Bài học rút ra (Lessons Learned)
> **Luôn cập nhật `settings_prod.py` mỗi khi thay đổi `settings.py`.**
>
> Vì hệ thống sử dụng 2 file settings riêng biệt (`settings.py` cho dev, `settings_prod.py` cho production/docker), mỗi khi thêm app mới, context processor, middleware, hoặc bất kỳ cấu hình nào vào `settings.py`, phải **đồng bộ tương ứng** vào `settings_prod.py`.
> Hoặc, cân nhắc refactor để `settings_prod.py` kế thừa từ `settings.py` bằng cách:
> ```python
> from .settings import *  # Import tất cả settings dev
> # Override chỉ những gì cần thay đổi cho production
> DEBUG = False
> ...
> ```
