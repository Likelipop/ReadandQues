import logging
from urllib.parse import urlparse
from newspaper import Article as NewspaperArticle
from .formatter import to_markdown

logger = logging.getLogger(__name__)

def crawl_article_content(url: str) -> dict:
    """
    Nhận vào một URL bài báo tiếng Anh, cào dữ liệu và trả về dict gồm title, content, và source_name.
    Content được định dạng dưới dạng Markdown thông qua hàm to_markdown.
    """
    try:
        # Extract source domain name from URL
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path.split('/')[0]
        source_name = domain.replace('www.', '').strip() if domain else "Unknown"

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
            
        formatted_content = to_markdown(article.text.strip())
            
        return {
            "success": True,
            "title": article.title.strip(),
            "content": formatted_content,
            "source_name": source_name,
        }
        
    except Exception as e:
        logger.error(f"Lỗi khi cào URL {url}: {str(e)}")
        return {
            "success": False,
            "error": f"Lỗi kết nối hoặc phân tích cú pháp: {str(e)}"
        }