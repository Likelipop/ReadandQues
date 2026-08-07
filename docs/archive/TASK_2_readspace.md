# Tài liệu Kế hoạch Triển khai: Task 2 - Readspace (Không Gian Đọc Báo)

## 1. Mục tiêu (Objectives)
- Cải tạo giao diện và logic hiện tại từ mô hình "Phòng thi" (Exam Room) có chứa Quiz bên cạnh sang mô hình "Không gian đọc báo" (Reading Space) tối ưu cho việc đọc và sử dụng Smart Ink.
- Chuyển logic liên quan sang một ứng dụng (app) Django mới có tên `readspace` để phân tách trách nhiệm (separation of concerns), giữ app `articles` nhẹ nhàng hơn hoặc chuyên biệt hơn.
- Cấu trúc lại giao diện (Layout) thành 3 cột, trong đó bài báo nằm ở giữa với kích thước lớn nhất.
- Di chuyển phần bài viết liên quan (Related articles) xuống dưới bài đọc thay vì đặt ở sidebar như hiện tại.
- Tạm thời gỡ bỏ Quiz ra khỏi layout, chỉ giữ lại thanh công cụ (Toolbar) gồm Marker, Eraser, và tính năng Smart Ink (Paraphrase).
- Đảm bảo các chức năng cốt lõi (lưu marker, đếm lượt đọc) vẫn hoạt động mượt mà.

## 2. Phân tích hiện trạng (Current State Analysis)
- **Kiến trúc app:** Trang chi tiết bài báo nằm trong app `articles` (`articles/views.py`), view `article_detail`.
- **Giao diện:** Đang dùng layout 2 cột (50/50), kết hợp giữa `_article_content.html` và `_quiz_sidebar.html`. Header có tính chất phòng thi (Back to Dashboard, title, timer, score).
- **Javascript (`_scripts.html`):** Rất cồng kềnh (~37KB) do chứa cả logic timer, highlight, state management, quiz submission và polling.
- **Tính năng nổi bật:** Smart Ink hoạt động thông qua việc chọn text -> bôi đen bằng Marker -> gọi API -> trả về nội dung Paraphrase hiển thị. Dữ liệu này được lưu xuống collection `attempts`. Các bài viết liên quan được lấy qua ChromaDB và BM25.
- **URL & Routing:** Routing hiện tại đang được gom chung vào app `articles`. Cần thiết kế lại routing cho `readspace`.

## 3. Thiết kế chi tiết (Detailed Design)

### 3.1. Thiết kế Giao diện (Layout)
Chuyển từ Layout 2 cột sang Layout 3 cột. Cột giữa sẽ là cột chính chứa bài báo để tối ưu trải nghiệm đọc (typography, spacing). Cột trái và phải đóng vai trò là không gian cho các tính năng mở rộng trong tương lai.

**Wireframe ASCII Art:**
```text
+-----------------------------------------------------------------------------------+
| HEADER (Logo, Back to Dashboard, Title, Profile/Settings)                         |
+----------------+-------------------------------------------------+----------------+
| CỘT TRÁI       | CỘT GIỮA (Bài báo chính)                        | CỘT PHẢI       |
| (Khoảng 20%)   | (Khoảng 60%)                                    | (Khoảng 20%)   |
|                |                                                 |                |
| [Future Use]   | +---------------------------------------------+ | [Future Use]   |
|                | | TOOLBAR (Marker, Eraser)                    | |                |
|                | +---------------------------------------------+ |                |
|                | |                                             | |                |
|                | | Tựa đề bài báo                              | |                |
|                | | (Metadata: Ngày, Lượt đọc...)               | |                |
|                | |                                             | |                |
|                | | [ Nội dung bài báo - render iframe hoặc     | |                |
|                | |   raw HTML. Hỗ trợ Smart Ink & Highlight ]  | |                |
|                | |                                             | |                |
|                | +---------------------------------------------+ |                |
|                |                                                 |                |
|                | +---------------------------------------------+ |                |
|                | | RELATED ARTICLES (Bài viết liên quan)       | |                |
|                | | - Bài 1                                     | |                |
|                | | - Bài 2                                     | |                |
|                | +---------------------------------------------+ |                |
+----------------+-------------------------------------------------+----------------+
```

### 3.2. Cấu trúc App `readspace`
- App `readspace` sẽ đảm nhiệm view hiển thị không gian đọc và xử lý các API liên quan đến trải nghiệm đọc (highlighting, smart ink) của không gian này.
- **Views chính:**
  - `readspace_view`: Phục vụ trang HTML chính.
  - `raw_html_view`: Trả về nội dung bài đọc để đưa vào iframe (nếu vẫn dùng iframe).
  - API views: `smart_paraphrase_api`, `save_highlight_api` (được tách từ view submit hiện tại).

## 4. Các file cần tạo/sửa/xóa (Files to create/modify/delete)

### Tạo mới App `readspace`
- `manage.py startapp readspace`
- **readspace/urls.py:** 
  - `path('<str:pk>/', views.readspace_view, name='readspace_detail')`
  - `path('<str:pk>/raw_html/', views.raw_html_view, name='raw_html_view')`
  - `path('api/<str:pk>/smart_paraphrase/', views.smart_paraphrase_view, name='smart_paraphrase')`
  - `path('api/<str:pk>/save_markers/', views.save_markers_view, name='save_markers')`
- **readspace/views.py:** 
  - Viết lại logic của `article_detail` (gọi `get_article_by_id_pipe`, `related_articles_pipe`).
  - Lược bỏ các phần liên quan đến `timer`, `score`, `quiz`.
- **readspace/templates/readspace/layout.html:** (Hoặc kế thừa `base.html` nếu phù hợp, nhưng tạo layout 3 cột mới với CSS Grid/Flexbox).
- **readspace/templates/readspace/includes:**
  - `_styles.html`: CSS cho 3 cột và bài báo.
  - `_toolbar.html`: Chỉ chứa Marker, Eraser.
  - `_article_content.html`: Khung hiển thị nội dung, nhúng iframe.
  - `_related_articles.html`: Trích xuất từ giao diện cũ, đặt dưới bài đọc.
  - `_scripts.html`: Loại bỏ toàn bộ logic quiz, timer, submit form thi. Chỉ giữ lại logic highlight engine, event listener cho Smart Ink, và lưu marker xuống DB.

### Chỉnh sửa/Xóa ở app `articles`
- Giữ nguyên (nếu vẫn cần cho mục đích cũ) hoặc **Deprecate** các url cũ của phòng thi nếu quyết định thay thế hoàn toàn. Theo task, đây là việc "Cải tạo", nên có thể route user từ Dashboard thẳng sang URL của `readspace` thay vì `articles`.
- Nếu bỏ hẳn "phòng thi" cũ, có thể xóa hoặc gom các HTML includes (`_quiz_sidebar.html`, v.v.) vào mục archive.

## 5. Luồng dữ liệu (Data Flow)

1. **Khởi tạo trang (Page Load):**
   - User truy cập `/readspace/<pk>/`.
   - `readspace_view` gọi `get_article_by_id_pipe` để lấy dữ liệu bài báo (từ collection `gold_articles`).
   - Gọi `related_articles_pipe` để lấy danh sách bài viết liên quan.
   - Render template 3 cột.

2. **Tương tác Smart Ink (Highlighting & Paraphrasing):**
   - User dùng Marker highlight 1 đoạn text trong cột giữa.
   - Client JS (`_scripts.html`) nhận diện event, lấy text và context.
   - Client gửi AJAX POST tới `/readspace/api/<pk>/smart_paraphrase/`.
   - API View gọi `smart_ink_pipe` -> (tìm cache trong `smart_paraphrase_cache` -> nếu không có thì LLM xử lý -> lưu cache).
   - Trả về JSON, Client JS hiển thị tooltip/popover paraphrase ngay tại vị trí highlight.

3. **Lưu Markers (Auto-save):**
   - Khi có thay đổi về highlight, Client gom data marker lưu vào localStorage.
   - Định kỳ hoặc khi rời trang (unload), Client gửi AJAX/Beacon data marker đến API `/readspace/api/<pk>/save_markers/`.
   - Backend cập nhật collection `attempts` để lưu trữ dữ liệu highlight cho user này.

## 6. Checklist triển khai (Implementation Checklist)

- [ ] **Bước 1: Khởi tạo & Cấu hình App**
  - [ ] Chạy lệnh `python manage.py startapp readspace`.
  - [ ] Khai báo `readspace` trong `INSTALLED_APPS` của `settings.py`.
  - [ ] Tạo `urls.py` trong `readspace` và include vào file `urls.py` gốc của project.
- [ ] **Bước 2: Xây dựng Layout & Template**
  - [ ] Tạo file `layout.html` thiết kế 3 cột.
  - [ ] Tích hợp CSS Flexbox/Grid cho tỷ lệ 20% - 60% - 20%.
  - [ ] Chuyển file `_toolbar.html`, `_article_content.html` từ app `articles` sang. Tinh giản phần Header (bỏ timer, score).
  - [ ] Di chuyển code hiển thị Related Articles thành một component `_related_articles.html` nằm dưới nội dung bài viết.
- [ ] **Bước 3: Viết Views & Pipelines integration**
  - [ ] Viết `readspace_detail` view: Gọi `get_article_by_id_pipe` và `related_articles_pipe`.
  - [ ] Viết `raw_html_view` tương tự như app cũ.
  - [ ] Chuyển endpoint `smart_paraphrase_view` sang `readspace/views.py`.
  - [ ] Viết API lưu markers độc lập, ghi đè vào collection `attempts` (thay vì dính liền với nộp bài quiz).
- [ ] **Bước 4: Tái cấu trúc Javascript**
  - [ ] Dọn dẹp file `_scripts.html`: Xóa bỏ code liên quan đến Quiz (Yes/No, MCQ, Fill in blank), xử lý state `status` (phòng thi).
  - [ ] Tối ưu hóa code highlight engine và đảm bảo kết nối đúng API endpoints mới (`/readspace/api/...`).
- [ ] **Bước 5: Kiểm thử (Testing)**
  - [ ] Đảm bảo bài đọc hiển thị đúng ở cột giữa.
  - [ ] Chức năng highlight, xoá highlight hoạt động.
  - [ ] Smart Ink gọi API paraphrase và trả về kết quả chính xác, có lưu vào cache.
  - [ ] Các marker được lưu xuống DB `attempts` khi thao tác.

## 7. Rủi ro và lưu ý (Risks & Notes)
- **Iframe & Layout:** Cột giữa 60% có thể hẹp hơn so với không gian 50% nhưng ẩn Sidebar ở bản cũ. Cần tinh chỉnh typography và padding để đảm bảo chữ không quá nhỏ hoặc ngắt dòng quá nhiều.
- **Refactor Javascript:** JS cũ (`_scripts.html`) dung lượng lớn và có thể dính chặt (tightly coupled) giữa logic Highlight và Quiz. Cần bóc tách cẩn thận, tránh làm hỏng engine Highlight. Khuyến nghị tách JS ra file static `.js` thay vì để trong `_scripts.html` để dễ maintain và debug.
- **Related Articles:** Lấy related articles sử dụng Vector Search có thể tốn thời gian, đảm bảo việc load chúng không làm chặn (block) việc render bài đọc chính. Có thể cân nhắc load related articles qua AJAX sau khi trang đã render xong để tăng tốc độ First Contentful Paint (FCP).
- **Dữ liệu Attempts:** Structure của collection `attempts` hiện tại có thể chứa các field dành cho điểm (score), đáp án (answers). API mới chỉ cập nhật field `markers`, cần cẩn thận không ghi đè mất hoặc làm lỗi schema hiện tại.
