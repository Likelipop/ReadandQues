# Kế Hoạch Triển Khai Task 6: Điều Chỉnh và Thiết Kế Lại Database

## 1. Mục Tiêu (Objectives)
- Mở rộng cấu trúc cơ sở dữ liệu hiện tại (MongoDB, SQLite, ChromaDB) để đáp ứng các tính năng mới từ Task 1-5 (Homepage Sections, Reading Analytics, User Highlights, Search Indexes).
- Đảm bảo tính mở rộng và độc lập (decoupling) giữa tầng dữ liệu (Data Layer) và logic nghiệp vụ (Business Logic/Pipeline).
- Tối ưu hóa truy vấn cho các tính năng hệ thống thông qua các bộ chỉ mục (Search Indexes) mới.

## 2. Phân Tích Hiện Trạng (Current State Analysis)
Hệ thống hiện tại phân tán dữ liệu ở 3 nơi:
- **MongoDB**: Đóng vai trò là Primary Storage cho dữ liệu bài báo (bronze, silver, gold), log (pipeline_logs), quá trình làm bài của người dùng (attempts), và các dữ liệu phụ trợ (paraphrases, rss_links).
- **SQLite (Django ORM)**: Xử lý thông tin người dùng (UserProfile, EmailVerification).
- **Vector/Keyword DBs**:
  - **ChromaDB**: Lưu trữ vector của bài báo phục vụ tìm kiếm ngữ nghĩa (Semantic Search) qua summary.
  - **BM25**: Hỗ trợ tìm kiếm từ khóa (Keyword Search).

*Hạn chế hiện tại:* 
Chưa có các bộ sưu tập (collections) riêng biệt để theo dõi lịch sử đọc, lịch sử highlight, thống kê từ vựng và lưu trữ cấu trúc linh hoạt cho Homepage Sections. Logic có nguy cơ bị rò rỉ (leak) ra ngoài package `database/`.

## 3. Thiết Kế Chi Tiết (Detailed Design)

### 3.1 Sơ Đồ Quan Hệ Dữ Liệu (Mermaid Diagram)

```mermaid
erDiagram
    UserProfile ||--o{ ReadingHistory : "has"
    UserProfile ||--o{ UserHighlight : "creates"
    UserProfile ||--o{ Attempt : "takes"
    UserProfile ||--o{ VocabTracking : "tracks"
    
    Article (Gold) ||--o{ ReadingHistory : "read_in"
    Article (Gold) ||--o{ UserHighlight : "highlighted_in"
    Article (Gold) ||--o{ Attempt : "has"
    
    HomepageSection ||--o{ Article (Gold) : "features"
    
    Article (Gold) {
        string _id
        string title
        string theme
        string genre
    }
    
    UserProfile {
        int id
        int total_articles_imported
        int streak
    }
    
    ReadingHistory {
        string user_id
        string article_id
        int read_duration_sec
        datetime last_read_at
        float completion_rate
    }
    
    UserHighlight {
        string user_id
        string article_id
        string highlighted_text
        string note
        datetime created_at
    }
    
    VocabTracking {
        string user_id
        string word
        int review_count
        float mastery_level
        datetime last_reviewed_at
    }
    
    HomepageSection {
        string section_id
        string section_type
        array items
        datetime updated_at
    }
```

### 3.2 Các Collection/Bảng Mới Cần Tạo

**MongoDB Collections:**
1. **`reading_history`**: Lưu lịch sử đọc của người dùng.
   - Fields: `_id`, `user_id`, `article_id`, `read_duration_sec`, `completion_rate`, `last_read_at`.
2. **`user_highlights`**: Lưu trữ các highlights và chú thích của user (phục vụ Recommendation).
   - Fields: `_id`, `user_id`, `article_id`, `highlighted_text`, `note`, `context`, `created_at`.
3. **`homepage_sections`**: Lưu cache/dữ liệu cho các section trên homepage (Trending, Daily Vocab, Recommendations).
   - Fields: `section_id` (e.g., 'daily_vocab', 'trending_articles'), `data` (JSON/Array), `updated_at`, `expires_at`.
4. **`vocab_tracking`**: Lưu quá trình học từ vựng của user (Daily Vocab feature).
   - Fields: `_id`, `user_id`, `word`, `context_article_id`, `review_count`, `mastery_level`, `last_reviewed_at`.

### 3.3 Các CRUD Functions Mới Cần Viết (trong `database/`)

- `database/mongo/reading_history.py`: `log_reading_session(user_id, article_id, duration, completion)`, `get_user_reading_history(user_id, limit)`
- `database/mongo/user_highlights.py`: `add_highlight(user_id, article_id, text, note)`, `get_user_highlights(user_id)`
- `database/mongo/homepage_sections.py`: `update_section_data(section_id, data)`, `get_section_data(section_id)`
- `database/mongo/vocab_tracking.py`: `track_vocab(user_id, word, article_id)`, `get_daily_vocab_for_user(user_id)`

### 3.4 Cập Nhật Chỉ Mục Tìm Kiếm (Search Indexes)
- **ChromaDB**: 
  - Thêm metadata bổ sung khi lưu vector bài báo: `theme`, `genre`, `difficulty_level` (nếu có) để lọc hiệu quả hơn.
  - CRUD operations update: `update_article_vector_metadata(...)`.
- **BM25**:
  - Tích hợp thêm các trường nội dung được cập nhật (ví dụ: keywords của bài báo).
  - Viết worker job để re-index BM25 định kỳ thay vì tính toán lại khi có request.

## 4. Các File Cần Tạo/Sửa/Xóa (Files to create/modify/delete)

**Tạo mới:**
- `database/mongo/reading_history.py`
- `database/mongo/user_highlights.py`
- `database/mongo/homepage_sections.py`
- `database/mongo/vocab_tracking.py`
- `database/models/user_tracking_models.py` (Pydantic models mới)

**Chỉnh sửa:**
- `database/mongo/articles.py` (Thêm query tối ưu cho Trending/Recommendations)
- `database/chroma/operations.py` (Update payload khi add vector)
- `database/BM25/operations.py` (Thêm cơ chế re-index)

## 5. Các Pipeline Jobs Mới Cần Tạo
- **`UpdateTrendingArticlesJob`**: Chạy định kỳ (ví dụ: mỗi giờ), tổng hợp `reading_history` và tính điểm trending, sau đó lưu vào collection `homepage_sections` với `section_id = 'trending_articles'`.
- **`GenerateDailyVocabJob`**: Lấy ra các từ khó từ các bài báo user đang/sắp đọc, lưu vào `homepage_sections` hoặc gửi trực tiếp vào `vocab_tracking`.
- **`UserRecommendationJob`**: Chạy hàng ngày, phân tích `reading_history` và `user_highlights` để tạo danh sách gợi ý cá nhân hóa, lưu cache vào `homepage_sections` với `section_id = f'recommendation_{user_id}'`.
- **`ReindexSearchDataJob`**: Cập nhật chỉ mục ChromaDB và BM25 cho các bài báo mới (Gold articles) một cách bất đồng bộ.

## 6. Luồng Dữ Liệu (Data Flow)

**Ví dụ Luồng Lịch Sử Đọc & Đề Xuất:**
1. **Event**: User mở bài báo và đọc. Phía client gửi heartbeat định kỳ.
2. **View/API**: API nhận request `/api/reading-history/log` và gọi một task bất đồng bộ (Celery/RQ) hoặc queue trực tiếp qua Pipeline.
3. **Pipeline Task**: Gọi function `log_reading_session` trong `database/mongo/reading_history.py`.
4. **Job Định Kỳ**: `UserRecommendationJob` quét `reading_history` của ngày, phân tích các chủ đề yêu thích (theme, genre từ bài báo user đã đọc), gọi mô hình AI/Heuristic để tìm bài mới.
5. **Caching**: Kết quả lưu vào `homepage_sections` để API homepage trả về nhanh chóng (độ trễ thấp).

## 7. Kế Hoạch Di Chuyển Dữ Liệu (Migration Plan)
1. **MongoDB**: Các collection mới sẽ trống lúc ban đầu. 
   - Có thể chạy một script migration phụ trích xuất `highlights` từ collection `attempts` (nếu có lưu) sang `user_highlights` mới để bootstrap Recommendation Engine.
2. **ChromaDB**: Xóa collection `articles` hiện tại hoặc tạo collection mới `articles_v2` với metadata đầy đủ (để không downtime). Sau đó chạy job backfill re-index toàn bộ dữ liệu từ `gold_articles` sang ChromaDB `articles_v2`. Swap tên khi hoàn thành.
3. **BM25**: Tạo lại index (pickle file) từ toàn bộ `gold_articles` hiện tại.

## 8. Checklist Triển Khai (Implementation Checklist)
- [ ] Thiết kế và tạo các Pydantic models mới (ReadingHistory, UserHighlight, v.v.).
- [ ] Viết các file module DB ops mới trong `database/mongo/`.
- [ ] Bổ sung metadata cho ChromaDB và viết lại module `database/chroma/operations.py`.
- [ ] Cập nhật/Tạo script re-index cho BM25.
- [ ] Xây dựng các background pipeline jobs (Trending, Recommendations, Daily Vocab).
- [ ] Viết unit tests cho các DB function mới.
- [ ] Thực hiện Data Migration (Bootstrap cho Search và Recommendation).

## 9. Rủi Ro và Lưu Ý (Risks & Notes)
- **Tốc độ phình to dữ liệu (Data Bloat)**: `reading_history` sẽ phình to rất nhanh. Cần thiết lập TTL (Time-To-Live) index trên MongoDB hoặc cơ chế archiving dữ liệu cũ (ví dụ: chỉ giữ lại 3 tháng cho recommend, nén lịch sử cũ).
- **Decoupling Violation**: Đảm bảo các views của Django KHÔNG import trực tiếp các module như `database.mongo.reading_history`. View phải gọi thông qua một lớp trung gian hoặc pipeline worker.
- **Tính nhất quán giữa MongoDB và ChromaDB/BM25**: Nếu bài báo Gold bị chỉnh sửa/xóa, cần có pipeline event tương ứng xóa/update trong ChromaDB và BM25.
