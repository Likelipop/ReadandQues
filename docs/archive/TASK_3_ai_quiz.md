# Implementation Plan: Tích hợp AI Quiz vào Reading Space (TASK 3)

## Mục tiêu (Objectives)
- Tích hợp tính năng AI Quiz trực tiếp vào không gian đọc (Reading Space) thông qua một công cụ trên Toolbar.
- Chuyển đổi giao diện sang chế độ chia đôi màn hình (Split View: Bài đọc | Quiz) khi người dùng kích hoạt.
- Tự động sinh câu hỏi bằng AI nếu chưa có, hoặc tải câu hỏi từ Database nếu đã tồn tại.
- Giữ nguyên các logic cốt lõi của phòng thi cũ (timer, scoring, tracking, state management) nhưng nâng cấp toàn diện trải nghiệm người dùng (UX).

## Phân tích hiện trạng (Current State Analysis)
- **Toolbar hiện tại:** Đã có các chức năng Marker, Eraser (và Smart Ink được trigger qua sự kiện click highlight).
- **Quiz logic:** Nằm rải rác trong các file `_quiz_sidebar.html` và `_scripts.html`.
- **Định dạng câu hỏi hỗ trợ:** `yes_no_notgiven`, `multiple_choice`, `fill_in_blank`.
- **AI Generation:** Sử dụng pipeline `single_article_pipe` gọi tới hàm `process_single_article` (tích hợp LangGraph AI).
- **Dữ liệu Database:** Quiz được lưu trữ trong document của bài báo tại đường dẫn `article.exams[0].quizzes` (collection `gold_articles`). Lịch sử làm bài được lưu trong collection `attempts`.
- **Xử lý Submit:** Gửi request đến `articles/<pk>/submit/`, hệ thống gọi `save_exam_attempt_pipe`. Sau khi lưu (`db_save_exam_attempt`), hệ thống sử dụng ChromaDB + BM25 để tìm và gợi ý các bài đọc liên quan.

## Thiết kế chi tiết (Detailed Design)

### 1. Giao diện (UI/UX)
- Thêm một nút (button) **"AI Quiz"** vào Toolbar hiện tại.
- Khi người dùng click vào nút này, layout chính của trang sẽ chuyển từ thiết kế cũ (ví dụ 3 cột) sang **chế độ 2 cột (Split View)**:
  - **Cột trái:** Hiển thị nội dung bài đọc (chiếm khoảng 60% màn hình).
  - **Cột phải:** Hiển thị AI Quiz Panel (chiếm khoảng 40% màn hình).
- **Trạng thái Loading:** Trong thời gian hệ thống đợi AI sinh câu hỏi, hiển thị Skeleton Loader hoặc Animation sinh động trong cột phải để người dùng biết hệ thống đang làm việc.

### 2. Logic Frontend (JavaScript)
- **Khởi tạo:**
  - Khi click "AI Quiz", gửi một AJAX request để kiểm tra trạng thái Quiz của bài viết (`article.exams`).
  - Nếu đã có dữ liệu: Tải câu hỏi từ DB và render.
  - Nếu chưa có: Kích hoạt API sinh Quiz (chạy `single_article_pipe`).
- **Polling:** Thực hiện polling thông qua endpoint `article_status` để cập nhật trạng thái xử lý (`processing` -> `completed`).
- **State Management:** Refactor lại logic trong `_scripts.html` để theo dõi Timer, Answer tracking, và duy trì `localStorage` (chống mất bài khi reload trang).

### 3. Tích hợp Backend
- **Endpoint kiểm tra/khởi tạo Quiz:** Cần điều chỉnh hoặc tạo mới một endpoint API nhỏ trả về JSON state của bài báo (để frontend dễ xử lý AJAX).
- **Submit Exam:** Giữ nguyên endpoint `articles/<pk>/submit/`. Sau khi submit, backend xử lý, trả về điểm số và danh sách related articles, frontend đảm nhiệm việc render kết quả lên panel.

## Các file cần tạo/sửa/xóa (Files to create/modify/delete)
- `templates/.../toolbar.html` (Modify): Thêm nút "AI Quiz" với các data-attributes phù hợp.
- `templates/.../reading_space.html` (Modify): Cập nhật grid/flex layout để hỗ trợ toggle CSS class cho chế độ 2 cột.
- `templates/.../_quiz_sidebar.html` (Modify): Cải tiến cấu trúc HTML/CSS (UX) để phù hợp hiển thị trong cột phải.
- `templates/.../_scripts.html` (Modify): Đóng gói và refactor lại các logic liên quan đến quiz (timer, localStorage, submit handlers).
- `static/js/reading_space.js` (Create/Modify): Thêm các hàm xử lý sự kiện click "AI Quiz", layout toggle, AJAX calls và long-polling.
- `views.py` (Modify): Đảm bảo các views trả về response JSON phù hợp khi Frontend gọi API kiểm tra bài viết.

## Luồng dữ liệu (Data Flow)
1. **User Action:** User click nút "AI Quiz" trên Toolbar.
2. **Check Data:** Frontend gọi API fetch thông tin article.
3. **Backend Logic (`get_article_by_id_pipe`):**
   - Nếu `article.exams` rỗng: Backend kích hoạt `single_article_pipe` (chạy background/async) và trả về status `processing`.
   - Nếu `article.exams` tồn tại: Trả về dữ liệu Quiz.
4. **Polling:** Nếu status là `processing`, Frontend liên tục gọi API `article_status` cho tới khi có kết quả.
5. **Render:** Dữ liệu Quiz được trả về và render vào Quiz Panel.
6. **Interaction:** User làm bài. Câu trả lời liên tục được lưu vào `localStorage`.
7. **Submit:** User nhấn "Submit". Frontend gọi AJAX POST đến `articles/<pk>/submit/`.
8. **Save & Suggest:** Backend gọi `save_exam_attempt_pipe`, tính điểm, lưu DB, query ChromaDB để lấy bài viết liên quan.
9. **Result Display:** Frontend nhận JSON response và render bảng điểm + Related articles.

## Wireframe (ASCII Art)

```text
+-----------------------------------------------------------------------+
| Header / Navigation                                                   |
+-----------------------------------------------------------------------+
| Toolbar: [Marker] [Eraser] | [AI Quiz (Active)]                       |
+------------------------------------------+----------------------------+
| Article Content (Left Col - 60%)         | AI Quiz Panel (Right - 40%)|
|                                          |                            |
| Title of the Article                     | [Timer: 15:00]             |
|                                          |                            |
| Lorem ipsum dolor sit amet, consectetur  | Question 1: Multiple Choice|
| adipiscing elit. Sed do eiusmod tempor   | ( ) Option A               |
| incididunt ut labore et dolore magna     | (x) Option B               |
| aliqua. Ut enim ad minim veniam, quis    | ( ) Option C               |
| nostrud exercitation ullamco laboris.    |                            |
|                                          | Question 2: Yes/No/NG      |
| Duis aute irure dolor in reprehenderit   | ( ) YES  ( ) NO  ( ) NG    |
| in voluptate velit esse cillum dolore.   |                            |
|                                          | Question 3: Fill in blank  |
| ...                                      | [_____________]            |
|                                          |                            |
|                                          |                            |
|                                          | [ Submit Answers ]         |
+------------------------------------------+----------------------------+
```

## Checklist triển khai (Implementation Checklist)
- [ ] **UI/UX:** Thêm nút AI Quiz vào template Toolbar.
- [ ] **CSS/Layout:** Viết CSS cho chế độ 2 cột (split-view) và hiệu ứng chuyển đổi (transition) mượt mà.
- [ ] **Frontend JavaScript:** Viết hàm handle click sự kiện chuyển đổi layout.
- [ ] **API Integration:** Triển khai luồng AJAX gọi API kiểm tra trạng thái Quiz và polling status.
- [ ] **Render Quiz:** Thiết kế lại HTML structure trong `_quiz_sidebar.html` đẹp hơn, hỗ trợ render các loại câu hỏi (Yes/No, MCQ, Fill in blank).
- [ ] **State Management:** Cập nhật script timer, update localStorage logic cho trạng thái làm bài.
- [ ] **Submit Form:** Gắn event listener chặn form submission thông thường, chuyển sang AJAX Submit và xử lý Response trả về (Score & Recommendations).
- [ ] **Refactoring:** Dọn dẹp code cũ ở `_scripts.html` để tách biệt rõ ràng trách nhiệm.

## Rủi ro và lưu ý (Risks & Notes)
- **Thời gian xử lý của AI (Latency):** Việc sinh câu hỏi bằng LangGraph AI có thể mất vài chục giây. Bắt buộc phải có UI Loading Status rõ ràng để tránh việc user reload trang liên tục.
- **Layout Shift:** Việc đổi từ layout 3 cột sang 2 cột có thể làm bể các Marker Highlight đã được tính toán vị trí tĩnh. Cần đảm bảo Marker được re-render hoặc CSS đủ linh hoạt để xử lý resize width.
- **Vấn đề Responsive:** Thiết kế Split View có thể không phù hợp trên các thiết bị Mobile/Tablet nhỏ. Có thể cần sử dụng Off-canvas sidebar hoặc Bottom Sheet trên mobile.
- **Xung đột State (`localStorage`):** Cần đảm bảo Key của localStorage được cấu trúc theo format chứa `article_id` cụ thể để tránh user làm nhiều bài báo bị ghi đè kết quả lên nhau.
