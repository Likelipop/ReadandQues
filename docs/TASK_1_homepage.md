# Kế Hoạch Triển Khai: Trùng Tu Trang Dashboard Thành Homepage

## 1. Mục Tiêu (Objectives)
- **Kiến trúc**: Tách rời logic của trang chủ khỏi app `accounts` để đảm bảo tính cohesion, tạo app `homepage` độc lập làm trung tâm.
- **UI/UX**: Chuyển đổi giao diện sang phong cách "trang báo điện tử" với nhiều khu vực (sections) phục vụ các mục đích khác nhau.
- **LEGO Architecture**: Thiết kế frontend theo dạng các module (LEGO blocks), giúp việc thêm, bớt, hoặc thay đổi thứ tự các sections trên trang chủ dễ dàng mà không ảnh hưởng tới toàn cục.
- **Tính năng mới**: Hỗ trợ tabs chủ đề (themes), section Hot News, Recommendation (dựa trên lịch sử), Daily Vocab, và tích hợp luôn danh sách "All Tests" vào cuối trang với tính năng lọc và phân trang.
- **Refactoring**: Cập nhật toàn bộ thuật ngữ và references từ "Dashboard" thành "Homepage".

## 2. Phân Tích Hiện Trạng (Current State Analysis)
- **Vị trí hiện tại**: Trang chủ đang được quản lý bởi `accounts/views.py` (`home_view`) và render template nguyên khối `accounts/templates/accounts/home.html`.
- **Dữ liệu**: View hiện tại đang gọi chung nhiều pipelines (`trending_articles`, `user_imported_articles`, `attempted_ids`) tạo thành một context lớn khó quản lý.
- **Dependencies**: Nhiều template khác (`articles/base.html`, `articles/detail.html`) đang sử dụng text "Dashboard" và có thể link tới view `all_tests_view` riêng lẻ trong app `articles`.

## 3. Thiết Kế Chi Tiết (Detailed Design)

### 3.1. Kiến Trúc App Mới (`homepage`)
Tạo một Django app hoàn toàn mới tên là `homepage`. App này sẽ chịu trách nhiệm chính trong việc tổng hợp dữ liệu từ các app/pipelines khác và render trang chủ.
- **`urls.py`**: Khai báo `path('', views.IndexView.as_view(), name='home')`. Việc giữ lại tên route `home` (hoặc `homepage:home`) giúp giảm thiểu lỗi gãy link (broken links) ở các app khác.
- **`views.py`**: Sử dụng class-based view (ví dụ `TemplateView` hoặc `ListView`) hoặc function-based view tùy mức độ phức tạp. View này sẽ lấy dữ liệu cho nhiều section. Nếu dữ liệu quá lớn, cân nhắc thiết kế view trả về từng phần (AJAX/HTMX) cho các section nặng.
- **`services.py`**: File trung gian chứa logic gọi tới các pipelines (ChromaDB, MongoDB collections như `gold_articles`, `attempts`) để tạo ra payload sạch đưa cho view.

### 3.2. Cấu Trúc Template (LEGO Sections)
Template chính sẽ không chứa code HTML lộn xộn mà chỉ đóng vai trò container:
```django
{% extends 'articles/base.html' %}

{% block content %}
<div class="homepage-container">
    {% include 'homepage/sections/ticker.html' %}
    {% include 'homepage/sections/hero_hot_news.html' %}
    
    <div class="grid-2-cols">
        {% include 'homepage/sections/daily_vocab.html' %}
        {% include 'homepage/sections/paraphrase_card.html' %}
    </div>

    {% include 'homepage/sections/recommendations.html' %}
    
    {% include 'homepage/sections/explore_tests.html' %}
</div>
{% endblock %}
```
Mỗi section sẽ tự xử lý giao diện UI của nó, nhận `context` từ view chính truyền xuống.

## 4. Các File Cần Tạo / Sửa / Xóa (Files to create/modify/delete)

### Tạo mới
- Khởi tạo app: `python manage.py startapp homepage`
- `homepage/urls.py`
- `homepage/views.py`
- `homepage/services.py` (fetching logic)
- `homepage/templates/homepage/index.html` (Main layout)
- `homepage/templates/homepage/sections/*.html` (Các file component: `ticker.html`, `hero.html`, `daily_vocab.html`, `recommendations.html`, `explore_tests.html`)

### Sửa
- **`ReadandQues/settings.py`**: Thêm `'homepage'` vào `INSTALLED_APPS`.
- **`ReadandQues/urls.py`**: 
  - `path('', include('homepage.urls'))` (Cấp quyền quản lý route `/` cho app mới).
- **`accounts/urls.py`**: Xóa `path('', views.home_view, name='home')`.
- **`accounts/views.py`**: Xóa hoặc deprecate `home_view`.
- **`articles/templates/articles/base.html`**:
  - Đổi text: `Dashboard` -> `Homepage`.
  - Cập nhật link cho nút All Tests để cuộn xuống (scroll) phần Explore ở Homepage, hoặc cập nhật logic phù hợp.
- **`articles/templates/articles/detail.html`**:
  - Đổi breadcrumb/nút back: `← Dashboard` -> `← Homepage`.
- **`articles/urls.py` & `articles/views.py`**:
  - Deprecate route `all-tests` (nếu đưa thẳng vào trang chủ), hoặc đổi thành một dạng fallback / standalone view.

### Xóa (hoặc Move)
- Xóa `accounts/templates/accounts/home.html` (Nên backup hoặc di chuyển `paraphrase_card.html` sang thư viện component chung hoặc app `homepage`).

## 5. Luồng Dữ Liệu (Data Flow)

1. **User request** tới `/`.
2. `homepage.views.IndexView` nhận request.
3. View gọi các hàm trong `homepage/services.py`:
   - `get_hot_news()`: Lấy tin nổi bật (VD: ngày gần nhất, điểm cao nhất).
   - `get_recommendations(user)`: Gọi `related_articles_pipe` từ lịch sử (history) của người dùng hoặc ngẫu nhiên nếu chưa đăng nhập.
   - `get_daily_vocab()`: Query từ vựng mới trong ngày.
   - `get_explore_tests(filters, page)`: Tích hợp logic của `all_tests_view` cũ, lấy `gold_articles` (status='completed') kèm theo pagination.
4. Trả context dictionary về cho `homepage/index.html`.
5. Render ra từng section.

## 6. Wireframe (ASCII Art)

```text
+-----------------------------------------------------------------------+
| HEADER: [Logo]   [Themes: All | Tech | Health...]   [User Profile]    |
+-----------------------------------------------------------------------+
| [TICKER] BREAKING NEWS: Article Title 1 • Article Title 2 • Article 3 |
+-----------------------------------------------------------------------+
|                                                                       |
|  +-------------------------------------+ +-------------------------+  |
|  |                                     | | [DAILY VOCAB]           |  |
|  |       [HERO / HOT NEWS]             | | Word: "Serendipity"     |  |
|  |       Large Image                   | | Meaning: ...            |  |
|  |       Bold Headline                 | +-------------------------+  |
|  |       Excerpt & Read More button    | +-------------------------+  |
|  |                                     | | [INTERACTIVE PARAPHRASE]|  |
|  |                                     | | (Moved from old dash)   |  |
|  +-------------------------------------+ +-------------------------+  |
|                                                                       |
+-----------------------------------------------------------------------+
| [RECOMMENDATIONS] Based on your history                               |
|  +--------------+  +--------------+  +--------------+  +-----------+  |
|  |  Rec Art 1   |  |  Rec Art 2   |  |  Rec Art 3   |  | Rec Art 4 |  |
|  +--------------+  +--------------+  +--------------+  +-----------+  |
+-----------------------------------------------------------------------+
| [EXPLORE / ALL TESTS]                                                 |
| Filters: [Theme v] [Difficulty v] [Sort v]                            |
| --------------------------------------------------------------------- |
| 1. Article List Item (Thumbnail, Title, Metadata)                     |
| 2. Article List Item (Thumbnail, Title, Metadata)                     |
| 3. Article List Item (Thumbnail, Title, Metadata)                     |
|                                                                       |
|                       [<< Prev] [1] [2] [3] [Next >>]                 |
+-----------------------------------------------------------------------+
| FOOTER: Links, Newsletter, Copyright                                  |
+-----------------------------------------------------------------------+
```

## 7. Checklist Triển Khai (Implementation Checklist)

- [ ] **Bước 1**: Khởi tạo app `homepage`, cấu hình `INSTALLED_APPS` và gán URL `/` trong router chính.
- [ ] **Bước 2**: Di chuyển và dọn dẹp view/url `home` từ app `accounts`. Sửa tất cả các references (HTML templates) từ Dashboard -> Homepage.
- [ ] **Bước 3**: Xây dựng cấu trúc thư mục templates cho kiến trúc LEGO (main `index.html` và thư mục `sections/`).
- [ ] **Bước 4**: Di chuyển `paraphrase_card` và các UI thành phần cũ (hero, ticker) sang `homepage/sections`. Đảm bảo code cũ vẫn chạy được trên app mới.
- [ ] **Bước 5**: Viết logic backend (trong `services.py`) để lấy data cho:
  - Ticker & Hero (Hot News).
  - Recommendations (fallback về trending nếu user mới/chưa đăng nhập).
  - Daily Vocab (thiết kế tạm mô hình random vocab nếu chưa có model riêng).
- [ ] **Bước 6**: Refactor tính năng `All Tests`:
  - Tạo section list bài đọc.
  - Implement phân trang (Django Paginator) và Query Params filters (`?theme=...`).
  - Hủy view `all_tests` cũ (nếu không cần URL riêng `/all-tests/`).
- [ ] **Bước 7**: Xây dựng CSS/Grid layout theo đúng phong cách báo chí.
- [ ] **Bước 8**: Testing luồng người dùng (Khách ẩn danh vs User đã đăng nhập, tốc độ load trang, CSS responsiveness).

## 8. Rủi Ro và Lưu Ý (Risks & Notes)

- **Hiệu suất (Performance)**: Lấy dữ liệu cho quá nhiều phần (Hot News, Recommendations, Phân trang All Tests, Vocab) trong một request duy nhất có thể làm trang tải chậm. 
  - *Giải pháp*: Nên sử dụng Django Cache (cache theo block template hoặc view cache). Hoặc dùng **HTMX/Fetch API** để load bất đồng bộ những section nặng như Recommendations sau khi trang chủ đã load xong (Lazy loading).
- **Trải nghiệm filter All Tests**: Vì đặt ở cuối trang, nếu filter/phân trang mà reload lại toàn bộ trang và người dùng bị đẩy lên đầu trang thì UX rất tệ. 
  - *Giải pháp*: Sử dụng HTMX hoặc AJAX để thay thế bảng danh sách All tests mà không cần reload cả trang, hoặc gắn HTML Anchor url (`#explore-section`) vào các nút phân trang.
- **Gãy liên kết**: Đảm bảo tất cả các url names (`{% url 'home' %}`) ở các app khác vẫn đang mapping chính xác về app `homepage` mới. Nên giữ nguyên Name `'home'` thay vì đổi thành `'homepage'` nếu muốn ít rủi ro nhất.
- **Khởi tạo Data**: Section Daily Vocab cần có dữ liệu mẫu. Có thể lấy ngẫu nhiên từ corpus văn bản hoặc tạo 1 Collection nhỏ để quản lý. Thống nhất luồng này trước khi render lên UI.
