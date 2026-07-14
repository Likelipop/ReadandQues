import logging
from newspaper import Article as NewspaperArticle

logger = logging.getLogger(__name__)

def crawl_article_content(url: str) -> dict:
    """
    Nhận vào một URL bài báo tiếng Anh, cào dữ liệu và trả về dict gồm title và content.
    """
    try:
        # Khởi tạo instance với keep_article_html=False để chỉ lấy plain text cho nhẹ DB
        article = NewspaperArticle(url, keep_article_html=False)
        article.download()
        article.parse()
        
        # Kiểm tra nếu nội dung trích xuất bị rỗng
        if not article.text or not article.title:
            return {
                "success": False,
                "error": "Không thể trích xuất nội dung từ URL này. Vui lòng thử trang báo khác."
            }
            
        return {
            "success": True,
            "title": article.title.strip(),
            "content": article.text.strip()
        }
        
    except Exception as e:
        logger.error(f"Lỗi khi cào URL {url}: {str(e)}")
        return {
            "success": False,
            "error": f"Lỗi kết nối hoặc phân tích cú pháp: {str(e)}"
        }