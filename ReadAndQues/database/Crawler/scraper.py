import logging
from urllib.parse import urlparse
from newspaper import Article as NewspaperArticle
from .formatter import to_markdown

logger = logging.getLogger(__name__)

def _extract_images(article: NewspaperArticle) -> tuple[str | None, list[str]]:
    """Extract valid image hotlink URLs from NewspaperArticle instance."""
    all_images = []
    top_image = article.top_image.strip() if article.top_image else None
    
    if top_image and not (top_image.startswith("http://") or top_image.startswith("https://")):
        top_image = None
        
    raw_images = list(article.images) if article.images else []
    for img in raw_images:
        img_url = img.strip()
        if img_url.startswith("http://") or img_url.startswith("https://"):
            # Exclude SVG icons, logos, tracking pixels where possible
            lower_url = img_url.lower()
            if not any(ext in lower_url for ext in ['.svg', 'pixel', 'avatar', 'sprite']):
                if img_url not in all_images:
                    all_images.append(img_url)
                    
    if top_image:
        if top_image in all_images:
            all_images.remove(top_image)
        all_images.insert(0, top_image)
    elif all_images:
        top_image = all_images[0]
        
    return top_image, all_images


def crawl_article_content(url: str) -> dict:
    """
    Nhận vào một URL bài báo tiếng Anh, cào dữ liệu và trả về dict gồm title, content, source_name, image_url, và image_urls.
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
        top_image, image_list = _extract_images(article)
            
        return {
            "success": True,
            "title": article.title.strip(),
            "content": formatted_content,
            "source_name": source_name,
            "image_url": top_image,
            "image_urls": image_list,
        }
        
    except Exception as e:
        logger.error(f"Lỗi khi cào URL {url}: {str(e)}")
        return {
            "success": False,
            "error": f"Lỗi kết nối hoặc phân tích cú pháp: {str(e)}"
        }