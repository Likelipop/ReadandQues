# Kế hoạch Triển khai (Implementation Plan): Thiết kế lại Header và Footer

## 1. Mục tiêu (Objectives)
- Cải tiến giao diện Header và Footer theo phong cách của các trang báo chí và tin tức chuyên nghiệp (như VnExpress, BBC, NYT).
- Tái cấu trúc thanh điều hướng (Navigation Bar) để tăng tính khám phá:
  - Xóa bỏ hoàn toàn mục "All Tests".
  - Thêm liên kết quay lại Trang chủ (Homepage) một cách trực quan.
  - Sử dụng các chủ đề (Themes) làm các tab điều hướng chính.
  - Bổ sung khu vực hiển thị các chủ đề/đề mục nóng hổi (Trending Topics) để thu hút người dùng.
- Nâng cấp Footer thành một không gian cung cấp thông tin toàn diện thay vì chỉ hiển thị dòng bản quyền.
- Đảm bảo tính nhất quán của UI/UX và thiết kế Reponsive, đồng thời không phá vỡ giao diện độc lập của trang Detail (Readspace).

## 2. Phân tích hiện trạng (Current State Analysis)
- **Base Template:** `articles/templates/articles/base.html`
- **Header hiện tại:**
  - Chứa Logo (emoji + gradient text) `READQUES`.
  - Global Omni Search Bar (hiện chỉ hỗ trợ hành vi paste URL).
  - Danh sách Nav links: Dashboard, All Tests, Stars count, Username, Logout/Login/Register.
  - Sử dụng Tailwind CSS với các lớp: `sticky top-0`, `bg-white/80`, `backdrop-blur`, `max-w-6xl`.
- **Footer hiện tại:**
  - Thiết kế rất cơ bản, chỉ có dòng chữ copyright: `&copy; 2026 Reading Academic Reading & Quiz Generator`.
  - Tailwind CSS: `bg-white border-t`, `py-6`.
- **Các View liên quan:** 
  - Routing: `home`, `articles:all_tests` (cần xóa), `profile`, `logout`, `login`, `register`.
  - Detail page (readspace) có một header riêng biệt, tối giản (dark theme, Back button, title, timer, score). Cần đảm bảo file template của trang này không bị ghi đè bởi Header mới.
- **Danh sách Themes (ThemeCategory Enum):** Economy, Society, Education, Technology, Science, Environment, Culture, Health, General.

## 3. Thiết kế chi tiết (Detailed Design)

### 3.1. Header Design (Cảm hứng từ News Sites)
Cấu trúc Header sẽ được chia làm 4 dải (bars) ngang xếp chồng lên nhau:
1. **Top Bar (Thanh tiện ích trên cùng):**
   - Trái: Hiển thị Ngày tháng hiện tại hoặc một thông điệp chào mừng nhỏ.
   - Phải: Khu vực người dùng (Stars count, Username/Dashboard/Profile, Logout) hoặc Auth links (Login/Register).
2. **Main Branding Bar (Khu vực trung tâm):**
   - Trái/Giữa: Logo READQUES thật to, nổi bật, phong cách Typogaphy báo chí.
   - Phải: Dịch chuyển Omni Search Bar (Paste URL) về bên phải, với thiết kế gọn gàng hơn.
3. **Navigation Bar (Thanh điều hướng chủ đề):**
   - Nút Homepage link (Biểu tượng ngôi nhà 🏠).
   - Danh sách các danh mục ngang (nguồn từ ThemeCategory): Technology, Science, Health, Economy, Society, Education, Environment, Culture. 
   - Thanh này cần hỗ trợ cuộn ngang (scroll) trên thiết bị di động.
4. **Trending Bar (Thanh tin tức nóng):**
   - Dải băng chạy nhỏ bên dưới Navigation, hiển thị: `Trending: [Tên bài viết 1] • [Tên bài viết 2] • ...`.

### 3.2. Footer Design
Footer sẽ được mở rộng bằng hệ thống lưới (CSS Grid), chia thành các cột rõ ràng:
- **Cột 1 (Branding & About):** Logo READQUES và mô tả ngắn (Slogan) về nền tảng.
- **Cột 2 (Categories):** Danh sách liên kết tới các Themes để điều hướng nhanh.
- **Cột 3 (Legal & Help):** Các liên kết hệ thống: About Us, Privacy Policy, Terms of Service, Contact (Dạng placeholder URL `#`).
- **Cột 4 (Stay Updated):** Social media icons (Facebook, X, LinkedIn) hoặc form đăng ký Newsletter.
- **Bottom Bar:** Dải text chứa Copyright hiện tại, được căn giữa ở tận cùng.

### 3.3. Wireframe (ASCII Art)

#### Header Wireframe
```text
+-----------------------------------------------------------------------------+
| T5, 30 Tháng 7, 2026                                 ⭐ 10 | [Username] ▾   |
|-----------------------------------------------------------------------------|
|                                                                             |
|   [ 📖 READQUES ]                                       [ Paste URL... 🔍 ] |
|                                                                             |
|-----------------------------------------------------------------------------|
| 🏠 Home | Technology | Science | Health | Economy | Society | Education | ≡ |
|-----------------------------------------------------------------------------|
| 📈 TRENDING: Tác động của AI đến giáo dục  •  Biến đổi khí hậu 2026         |
+-----------------------------------------------------------------------------+
```

#### Footer Wireframe
```text
+-----------------------------------------------------------------------------+
|                                                                             |
|   [ 📖 READQUES ]          CATEGORIES             USEFUL LINKS              |
|   AI-powered reading       - Technology           - About Us                |
|   & quiz generator for     - Science              - Privacy Policy          |
|   academic learners.       - Health               - Terms of Service        |
|                            - Economy              - Contact                 |
|                                                                             |
|   [f] [t] [in] [ig]                                                         |
|                                                                             |
|-----------------------------------------------------------------------------|
|  © 2026 Reading Academic Reading & Quiz Generator. All rights reserved.     |
+-----------------------------------------------------------------------------+
```

## 4. Các file cần tạo/sửa/xóa (Files to create/modify/delete)

1. **Thêm file mới: `articles/context_processors.py`**
   - Hàm trả về dictionary chứa dữ liệu để render Navigation và Trending toàn cục.
2. **Sửa file: `READQUES/settings.py`**
   - Đăng ký `articles.context_processors.global_news_context` vào danh sách `TEMPLATES['OPTIONS']['context_processors']`.
3. **Sửa file: `articles/templates/articles/base.html`**
   - Thay thế các khối `<header>` và `<footer>` cũ bằng mã HTML/Tailwind CSS mới theo thiết kế.
   - Xóa `{% url 'articles:all_tests' %}`.

## 5. Luồng dữ liệu (Data Flow)

1. **Context Processor (`articles/context_processors.py`):** 
   - Lấy danh sách enum `ThemeCategory` (loại bỏ 'General' nếu cần) gán vào biến `categories`.
   - Lấy ngẫu nhiên hoặc truy vấn 3-5 bài test/article phổ biến gán vào biến `trending_topics`.
2. **Template Rendering (`base.html`):** 
   - Nhận `categories` và `trending_topics` từ mọi request.
   - Dùng thẻ `{% for cat in categories %}` để in ra các menu link.
   - Các link category sẽ trỏ về `home` hoặc 1 view lọc chuyên biệt (ví dụ: `/?theme=Technology`).
3. **User Action:** 
   - Người dùng click vào tab "Science" -> Hệ thống fetch lại trang chủ với bài viết được filter theo Science.
   - Các hành vi tìm kiếm (Paste URL) vẫn tiếp tục trigger logic Javascript như cũ.

## 6. Checklist triển khai (Implementation Checklist)

- [ ] **Bước 1: Cấu hình Data & Context Processor**
  - [ ] Tạo file `articles/context_processors.py`.
  - [ ] Viết hàm `global_news_context` trả về `themes` và `trending`.
  - [ ] Cập nhật `settings.py` để inject context này vào template.
- [ ] **Bước 2: Phát triển UI Header**
  - [ ] Dựng Top Bar cho hiển thị ngày/giờ và thông tin người dùng.
  - [ ] Dựng Main Branding Bar chứa Logo và Search Input. Đảm bảo input ID vẫn giữ nguyên để không làm vỡ JS logic.
  - [ ] Dựng Navigation Bar với Home Icon và loop qua danh sách Themes.
  - [ ] Xóa code hiển thị "All Tests".
  - [ ] Dựng Trending Ticker.
- [ ] **Bước 3: Phát triển UI Footer**
  - [ ] Áp dụng `grid` layout với Tailwind (`grid-cols-1 md:grid-cols-4`).
  - [ ] Dựng cột thông tin nền tảng, danh mục (lấy từ context), và link hỗ trợ.
  - [ ] Đặt dòng copyright phía dưới cùng.
- [ ] **Bước 4: CSS & Styling Review**
  - [ ] Thêm các class responsive (`hidden md:flex`, `overflow-x-auto` cho Navbar mobile).
  - [ ] Bỏ class `max-w-6xl` chung chung nếu thiết kế Header mới yêu cầu full-width background, chỉ wrap nội dung ở giữa bằng `max-w-6xl mx-auto`.
- [ ] **Bước 5: Kiểm thử (Testing)**
  - [ ] Truy cập trang chủ, đảm bảo Header/Footer mới hiển thị tốt.
  - [ ] Kiểm tra responsive trên kích thước màn hình nhỏ.
  - [ ] Xác minh trang Detail (Readspace) vẫn giữ được Header tối màu, không bị ghi đè.

## 7. Rủi ro và lưu ý (Risks & Notes)
- **Hiệu suất (Performance):** Context processor chạy trên **mọi** page load. Truy vấn `trending_topics` cần được cache (`django.core.cache`) ví dụ cache 15-30 phút để không tạo gánh nặng cho Database.
- **Tính năng lọc (Filtering):** Khi user click vào Navigation Tabs (Themes), backend phải sẵn sàng xử lý param này. (VD: view `home` cần filter nếu có `request.GET.get('theme')`).
- **Xung đột JavaScript:** Header hiện tại có thanh Omni Search, có thể có script đi kèm để parse URL. Cần giữ nguyên cấu trúc class/id quan trọng (`<form>`, `<input>`) để không làm hỏng tính năng xử lý URL text.
- **Trang Readspace:** Layout của Detail page có header đặc biệt. Phải đảm bảo file HTML của Detail page (vd: `articles/readspace.html`) không bị gọi nhầm header này, hoặc nó overrides `{% block header %}` rỗng để dùng custom design.
