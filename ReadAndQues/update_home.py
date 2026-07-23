import re

with open('/home/likelipop/Project/ReadandQues/ReadAndQues/accounts/templates/accounts/home.html', 'r', encoding='utf-8') as f:
    content = f.read()

replacements = {
    "Trang chủ - IELTS AI Reading Quiz": "Home - AI Reading Practice Quiz",
    "IELTS AI Reading Practice": "AI Reading Practice",
    "Nâng cao điểm số IELTS Reading bằng cách luyện tập với các bài báo thực tế từ khắp nơi trên thế giới. AI của chúng tôi sẽ phân tích văn bản và thiết lập câu hỏi theo đúng chuẩn đề thi thật.": "Improve your reading comprehension by practicing with real articles from around the world. Our AI will analyze the text and generate standardized reading comprehension questions.",
    "Xem tất cả bài test": "View all tests",
    "Chưa có tiêu đề": "No title",
    "Chưa có bài viết trending nào trong hệ thống.": "No trending articles in the system yet.",
    "Tiêu đề": "Title",
    "Nguồn": "Source",
    "Ngày tạo": "Created Date",
    "Trạng thái": "Status",
    "Hành động": "Action",
    "Làm bài tập": "Practice",
    "Xem chi tiết": "View Details",
    "Thư viện trống": "Library is empty",
    "Bạn chưa nhập bài báo tiếng Anh nào. Dán link bài báo để AI sinh quiz bài tập độc quyền cho bạn nhé!": "You haven't imported any articles yet. Paste an article link to let our AI generate an exclusive reading quiz for you!",
    "Nhập bài báo đầu tiên": "Import your first article",
    "IELTS Reading AI": "Reading AI",
    "IELTS": "Reading",
    "Đang sinh...": "Generating..."
}

for k, v in replacements.items():
    content = content.replace(k, v)

with open('/home/likelipop/Project/ReadandQues/ReadAndQues/accounts/templates/accounts/home.html', 'w', encoding='utf-8') as f:
    f.write(content)
