import os
import glob

replacements = {
    "Tất cả bài test - IELTS AI Reading Quiz": "All Tests - AI Reading Practice Quiz",
    "Tất cả đề thi IELTS Reading": "All Reading Practice Tests",
    "Danh sách toàn bộ các đề thi đã được biên dịch hoàn chỉnh. Luyện tập hoàn toàn miễn phí không giới hạn.": "List of all completed practice tests. Practice completely free and unlimited.",
    "Tìm kiếm đề thi...": "Search for tests...",
    "Chủ đề (Theme):": "Theme:",
    "Tất cả": "All",
    "Tất cả thể loại": "All genres",
    "Thể loại (Genre):": "Genre:",
    "Chưa có tiêu đề": "No title",
    "Không tìm thấy bài test nào phù hợp với bộ lọc hiện tại. Hãy chọn chủ đề khác hoặc tạo bài viết mới!": "No tests found matching the current filters. Please select a different theme or create a new article!",
    "Chưa có bài test nào": "No tests yet",
    "Trước": "Previous",
    "Tiếp": "Next",
    "Không tìm thấy bài test phù hợp": "No matching tests found",
    "Vui lòng kiểm tra lại từ khóa tìm kiếm của bạn.": "Please check your search keywords.",
    "Có lỗi xảy ra.": "An error occurred.",
    "Mạng chậm hoặc lỗi máy chủ, vui lòng thử lại.": "Slow network or server error, please try again.",
    "Dashboard": "Dashboard",
    "Có thể bạn sẽ thích": "You might also like",
    "Xem tất cả bài kiểm tra": "View all tests",
    "Dựa trên những gì bạn đã highlight": "Based on what you highlighted",
    "Đã nộp bài": "Submitted",
    "Bạn chưa điền đủ các câu trả lời. Bạn có chắc chắn muốn nộp bài?": "You haven't filled in all the answers. Are you sure you want to submit?",
    "AI đang phân tích bài viết và dựng đề thi...": "AI is analyzing the article and generating the test...",
    "Quá trình này thường mất từ 10-15 giây. Bạn có thể tranh thủ": "This process usually takes 10-15 seconds. You can take this time to",
    "đọc trước bài báo bên cánh trái.": "pre-read the article on the left.",
    "Trang Không Tồn Tại | ReadAndQues": "Page Not Found | ReadAndQues",
    "Trang Không Tồn Tại": "Page Not Found",
    "Đường dẫn bạn đang tìm kiếm không tồn tại hoặc đã được di chuyển.": "The path you are looking for does not exist or has been moved.",
    "Trở Về Trang Chủ": "Return to Home",
    "Lỗi Máy Chủ | ReadAndQues": "Server Error | ReadAndQues",
    "Lỗi Hệ Thống Tạm Thời": "Temporary System Error",
    "Hệ thống đã ghi nhận lỗi và đang được xử lý. Vui lòng thử lại sau ít phút.": "The system has logged the error and it is being processed. Please try again later.",
    "Thử Chạy Lại Trang Chủ": "Try Loading Home Page",
    "IELTS AI Reading Quiz": "AI Reading Practice Quiz",
    "IELTS Reading AI": "Reading AI",
    "IELTS Reading": "Reading",
    "IELTS": "Reading",
    "Nâng cao điểm số IELTS Reading bằng cách luyện tập với các bài báo thực tế từ khắp nơi trên thế giới. AI của chúng tôi sẽ phân tích văn bản và thiết lập câu hỏi theo đúng chuẩn đề thi thật.": "Improve your reading comprehension by practicing with real articles from around the world. Our AI will analyze the text and generate standardized reading comprehension questions."
}

files = glob.glob('/home/likelipop/Project/ReadandQues/ReadAndQues/articles/templates/**/*.html', recursive=True)

for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    for k, v in replacements.items():
        content = content.replace(k, v)
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

