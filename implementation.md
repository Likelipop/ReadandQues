# Kế hoạch triển khai lấy dữ liệu bài báo bằng Trafilatura

## 1. Mục tiêu

Tài liệu này mô tả cách thay bộ crawler hiện tại dùng `newspaper3k` bằng
Trafilatura, nhưng vẫn giữ nguyên luồng nghiệp vụ đang chạy của ReadAndQues:

```text
POST /articles/import/
  -> crawl_article_content(url)
  -> MongoDB document status=pending
  -> background thread
  -> LangGraph tạo analysis + exam
  -> MongoDB document status=completed/failed
```

Phạm vi triển khai:

- Trafilatura tải HTML, lấy nội dung chính và metadata.
- Giữ nguyên public contract `crawl_article_content(url) -> dict` để
  `articles/views.py` không phải viết lại toàn bộ.
- Nội dung gửi cho LangGraph vẫn nằm trong trường `content` của kết quả crawler
  và `original_text` trong MongoDB.
- Ảnh đại diện và danh sách ảnh được lấy từ Open Graph/Twitter metadata và thẻ
  `<img>` của HTML gốc.
- Bổ sung canonical URL, tác giả, ngày xuất bản, ngôn ngữ, số từ và metadata về
  lần crawl.
- Có kiểm tra URL cơ bản nhằm giảm nguy cơ SSRF trước khi server tải trang.
- Test crawler hoàn toàn bằng HTML giả lập, không gọi website thật.

Trafilatura 2.1 hỗ trợ `fetch_response()` để lấy HTTP response/final URL và
`bare_extraction()` để nhận một `Document` chứa text cùng metadata. `Document`
có thể chuyển thành dictionary bằng `.as_dict()`.

Tài liệu chính thức:

- Python usage: <https://trafilatura.readthedocs.io/en/latest/usage-python.html>
- Download API: <https://trafilatura.readthedocs.io/en/latest/downloads.html>
- Core functions: <https://trafilatura.readthedocs.io/en/latest/corefunctions.html>
- Settings: <https://trafilatura.readthedocs.io/en/latest/settings.html>

## 2. Hiện trạng của dự án

Crawler hiện tại nằm tại:

```text
ReadAndQues/articles/utils/crawler.py
```

Nó dùng `newspaper3k` và trả về contract:

```python
{
    "success": True,
    "title": "...",
    "content": "...",
    "source_name": "...",
    "image_url": "...",
    "image_urls": ["..."],
}
```

`import_article_view()` lấy dữ liệu này để tạo MongoDB document:

```python
pending_document = {
    "url": url,
    "title": crawl_res.get("title", ""),
    "original_text": crawl_res.get("content", ""),
    "source_name": crawl_res.get("source_name", "Unknown"),
    "image_url": crawl_res.get("image_url"),
    "image_urls": crawl_res.get("image_urls") or [],
    "status": "pending",
    "user_id": request.user.id,
    "created_at": datetime.utcnow(),
}
```

Vì vậy cách thay ít rủi ro nhất là giữ các key cũ và chỉ thêm key mới. Không đổi
`content` thành `text` ở public contract, vì view hiện tại đang đọc `content`.

## 3. Data contract sau khi triển khai

Kết quả thành công của crawler:

```python
{
    "success": True,
    "url": "https://url-nguoi-dung-nhap.example/article",
    "canonical_url": "https://final-url-sau-redirect.example/article",
    "title": "Article title",
    "content": "Nội dung chính đã làm sạch...",
    "source_name": "Example News",
    "author": "Jane Doe",
    "published_at": datetime(...),
    "language": "en",
    "word_count": 842,
    "image_url": "https://example.com/cover.jpg",
    "image_urls": [
        "https://example.com/cover.jpg",
        "https://example.com/figure-1.jpg",
    ],
    "crawl_metadata": {
        "crawler": "trafilatura",
        "final_url": "https://final-url-sau-redirect.example/article",
        "http_status": 200,
        "content_type": "text/html; charset=utf-8",
        "hostname": "example.com",
        "fingerprint": "...",
        "crawled_at": datetime(...),
    },
}
```

Kết quả thất bại phải luôn có cấu trúc ổn định:

```python
{
    "success": False,
    "error": "Thông báo an toàn cho người dùng",
    "error_code": "DOWNLOAD_FAILED",
}
```

Các `error_code` đề xuất:

| Mã | Ý nghĩa |
| --- | --- |
| `INVALID_URL` | URL không phải HTTP/HTTPS hoặc hostname không hợp lệ |
| `PRIVATE_ADDRESS` | URL trỏ tới loopback/private/link-local/reserved IP |
| `DOWNLOAD_FAILED` | Trafilatura không tải được trang |
| `HTTP_ERROR` | HTTP status không nằm trong 2xx |
| `UNSUPPORTED_CONTENT` | Response không phải HTML/XHTML |
| `EXTRACTION_FAILED` | Không tìm được nội dung chính |
| `CONTENT_TOO_SHORT` | Nội dung quá ngắn để tạo bài IELTS |
| `CONTENT_TOO_LARGE` | Nội dung vượt giới hạn xử lý của ứng dụng |
| `UNEXPECTED_ERROR` | Lỗi không dự kiến; chi tiết chỉ ghi vào server log |

## 4. Cài dependency

Chạy tại repository root, nơi có `pyproject.toml`:

```bash
uv add "trafilatura>=2.1,<3"
```

Lệnh này cập nhật `pyproject.toml` và `uv.lock`. Nếu team vẫn cài bằng
`requirements.txt`, đồng bộ lại file đó bằng quy trình dependency hiện hành của
team. Tối thiểu phải có dòng:

```text
trafilatura>=2.1,<3
```

Trong giai đoạn chuyển đổi, chưa xóa `newspaper3k`. Chỉ gỡ sau khi crawler mới
đã qua test và chạy thử với tập URL thật:

```bash
uv remove newspaper3k
```

Sau khi gỡ, kiểm tra lại `lxml-html-clean` trước khi xóa vì package khác có thể
vẫn dùng nó.

## 5. Cấu hình Trafilatura

Tạo file `ReadAndQues/trafilatura.cfg`:

```ini
[DEFAULT]
DOWNLOAD_TIMEOUT = 15
MAX_FILE_SIZE = 5000000
MIN_FILE_SIZE = 100
MIN_EXTRACTED_SIZE = 300
MIN_OUTPUT_SIZE = 200
MAX_TREE_SIZE = 500000
SLEEP_TIME = 1
```

Ý nghĩa:

- Timeout 15 giây để request Django không treo quá lâu.
- HTML tối đa 5 MB; ảnh không được tải về nên không tính vào giới hạn này.
- Yêu cầu tối thiểu 300 ký tự nội dung trích xuất.
- Giới hạn số node HTML để tránh trang bất thường tiêu tốn quá nhiều RAM/CPU.

Trong `ReadAndQues/ReadAndQues/settings.py`, thêm:

```python
TRAFILATURA_CONFIG_FILE = BASE_DIR / "trafilatura.cfg"
ARTICLE_MIN_WORDS = int(os.getenv("ARTICLE_MIN_WORDS", "120"))
ARTICLE_MAX_WORDS = int(os.getenv("ARTICLE_MAX_WORDS", "15000"))
ARTICLE_MAX_IMAGES = int(os.getenv("ARTICLE_MAX_IMAGES", "20"))
```

Các ngưỡng này thuộc nghiệp vụ ứng dụng nên đặt trong Django settings; timeout,
file size và tree size thuộc Trafilatura nên đặt trong `trafilatura.cfg`.

## 6. Thay `articles/utils/crawler.py`

Thay nội dung file bằng implementation dưới đây. Hàm public vẫn mang tên
`crawl_article_content()` để tương thích với view hiện tại.

```python
from __future__ import annotations

import ipaddress
import logging
import socket
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse

from django.conf import settings
from lxml import html as lxml_html
from trafilatura import bare_extraction, fetch_response
from trafilatura.settings import use_config

from .formatter import to_markdown


logger = logging.getLogger(__name__)

TRAFILATURA_CONFIG = use_config(str(settings.TRAFILATURA_CONFIG_FILE))


class CrawlError(Exception):
    """Lỗi crawler có mã ổn định và message an toàn cho client."""

    def __init__(self, code: str, public_message: str):
        super().__init__(public_message)
        self.code = code
        self.public_message = public_message


def _error(code: str, message: str) -> dict[str, Any]:
    return {
        "success": False,
        "error": message,
        "error_code": code,
    }


def _validate_public_http_url(url: str) -> None:
    """Chặn scheme lạ và hostname/IP nội bộ trước khi tải URL."""
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        raise CrawlError(
            "INVALID_URL",
            "URL phải bắt đầu bằng http:// hoặc https://.",
        )

    if not parsed.hostname:
        raise CrawlError("INVALID_URL", "URL không có tên miền hợp lệ.")

    if parsed.username or parsed.password:
        raise CrawlError(
            "INVALID_URL",
            "URL chứa thông tin đăng nhập và không được hỗ trợ.",
        )

    try:
        address_info = socket.getaddrinfo(
            parsed.hostname,
            parsed.port or (443 if parsed.scheme == "https" else 80),
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise CrawlError(
            "INVALID_URL",
            "Không thể phân giải tên miền của URL.",
        ) from exc

    for item in address_info:
        ip = ipaddress.ip_address(item[4][0])
        if any(
            (
                ip.is_private,
                ip.is_loopback,
                ip.is_link_local,
                ip.is_multicast,
                ip.is_reserved,
                ip.is_unspecified,
            )
        ):
            raise CrawlError(
                "PRIVATE_ADDRESS",
                "URL trỏ tới địa chỉ mạng không được phép.",
            )


def _parse_published_at(value: Any) -> datetime | None:
    """Chuyển ngày do Trafilatura trả về thành UTC datetime cho MongoDB."""
    if not value:
        return None

    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value).strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            logger.info("Không parse được publication date: %r", value)
            return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _first_src_from_srcset(srcset: str) -> str | None:
    """Lấy URL đầu tiên trong srcset='a.jpg 1x, b.jpg 2x'."""
    first_candidate = srcset.split(",", 1)[0].strip()
    if not first_candidate:
        return None
    return first_candidate.split()[0]


def _normalize_image_url(raw_url: str | None, base_url: str) -> str | None:
    if not raw_url:
        return None

    normalized = urljoin(base_url, raw_url.strip())
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None

    lowered = normalized.lower()
    blocked_markers = (".svg", "sprite", "tracking", "pixel", "avatar")
    if any(marker in lowered for marker in blocked_markers):
        return None

    return normalized


def _extract_images(
    html_content: bytes | str,
    base_url: str,
    limit: int,
) -> tuple[str | None, list[str]]:
    """
    Ưu tiên og:image/twitter:image, sau đó lấy ảnh trong nội dung HTML.

    Trafilatura có include_images=True, nhưng ảnh là structural element và phù
    hợp nhất với XML/Document. Project này chỉ cần URL ảnh, nên parse HTML gốc
    trực tiếp sẽ cho contract đơn giản và ổn định hơn.
    """
    try:
        tree = lxml_html.fromstring(html_content, base_url=base_url)
    except (ValueError, TypeError):
        return None, []

    candidates: list[str] = []

    metadata_xpaths = (
        '//meta[@property="og:image"]/@content',
        '//meta[@property="og:image:secure_url"]/@content',
        '//meta[@name="twitter:image"]/@content',
        '//meta[@name="twitter:image:src"]/@content',
    )
    for xpath in metadata_xpaths:
        candidates.extend(tree.xpath(xpath))

    for image in tree.xpath("//article//img | //main//img | //img"):
        raw_url = (
            image.get("src")
            or image.get("data-src")
            or image.get("data-lazy-src")
            or _first_src_from_srcset(image.get("srcset", ""))
        )
        if raw_url:
            candidates.append(raw_url)

    image_urls: list[str] = []
    for candidate in candidates:
        normalized = _normalize_image_url(candidate, base_url)
        if normalized and normalized not in image_urls:
            image_urls.append(normalized)
        if len(image_urls) >= limit:
            break

    top_image = image_urls[0] if image_urls else None
    return top_image, image_urls


def _extract_article(
    html_content: bytes | str,
    requested_url: str,
    final_url: str,
    http_status: int,
    content_type: str,
) -> dict[str, Any]:
    """Tách riêng extraction khỏi network để unit test không gọi Internet."""
    document = bare_extraction(
        html_content,
        url=final_url,
        output_format="python",
        with_metadata=True,
        include_comments=False,
        include_tables=False,
        include_images=False,
        favor_precision=True,
        target_language="en",
        date_extraction_params={
            "extensive_search": True,
            "original_date": True,
        },
        config=TRAFILATURA_CONFIG,
    )

    if document is None:
        raise CrawlError(
            "EXTRACTION_FAILED",
            "Không thể nhận diện nội dung chính của bài báo.",
        )

    extracted = document.as_dict()
    raw_text = (extracted.get("text") or getattr(document, "text", "") or "").strip()
    title = (extracted.get("title") or getattr(document, "title", "") or "").strip()

    if not raw_text or not title:
        raise CrawlError(
            "EXTRACTION_FAILED",
            "Bài báo không có tiêu đề hoặc nội dung có thể trích xuất.",
        )

    content = to_markdown(raw_text)
    word_count = len(content.split())

    if word_count < settings.ARTICLE_MIN_WORDS:
        raise CrawlError(
            "CONTENT_TOO_SHORT",
            f"Bài báo cần ít nhất {settings.ARTICLE_MIN_WORDS} từ để tạo đề.",
        )

    if word_count > settings.ARTICLE_MAX_WORDS:
        raise CrawlError(
            "CONTENT_TOO_LARGE",
            "Bài báo quá dài để xử lý trong một lần.",
        )

    parsed_final_url = urlparse(final_url)
    fallback_source = (parsed_final_url.hostname or "Unknown").removeprefix("www.")
    source_name = (
        extracted.get("sitename")
        or extracted.get("hostname")
        or fallback_source
    )

    image_url, image_urls = _extract_images(
        html_content,
        base_url=final_url,
        limit=settings.ARTICLE_MAX_IMAGES,
    )

    return {
        "success": True,
        "url": requested_url,
        "canonical_url": extracted.get("url") or final_url,
        "title": title,
        "content": content,
        "source_name": str(source_name).strip(),
        "author": extracted.get("author"),
        "published_at": _parse_published_at(extracted.get("date")),
        "language": extracted.get("language") or "en",
        "word_count": word_count,
        "image_url": image_url,
        "image_urls": image_urls,
        "crawl_metadata": {
            "crawler": "trafilatura",
            "final_url": final_url,
            "http_status": http_status,
            "content_type": content_type,
            "hostname": extracted.get("hostname") or fallback_source,
            "fingerprint": extracted.get("fingerprint"),
            "crawled_at": datetime.now(timezone.utc),
        },
    }


def crawl_article_content(url: str) -> dict[str, Any]:
    """Download và chuẩn hóa một URL bài báo thành contract của ứng dụng."""
    requested_url = url.strip()

    try:
        _validate_public_http_url(requested_url)

        response = fetch_response(
            requested_url,
            decode=True,
            with_headers=True,
            config=TRAFILATURA_CONFIG,
        )
        if response is None:
            raise CrawlError(
                "DOWNLOAD_FAILED",
                "Không thể tải nội dung từ URL này.",
            )

        status = int(response.status or 0)
        if status < 200 or status >= 300:
            raise CrawlError(
                "HTTP_ERROR",
                f"Trang báo trả về HTTP status {status}.",
            )

        final_url = response.url or requested_url

        # Kiểm tra lại URL sau redirect.
        _validate_public_http_url(final_url)

        headers = response.headers or {}
        content_type = str(
            headers.get("content-type")
            or headers.get("Content-Type")
            or ""
        )
        if content_type and not any(
            allowed in content_type.lower()
            for allowed in ("text/html", "application/xhtml+xml")
        ):
            raise CrawlError(
                "UNSUPPORTED_CONTENT",
                "URL không trả về một trang HTML.",
            )

        html_content = response.html if response.html is not None else response.data
        if not html_content:
            raise CrawlError(
                "DOWNLOAD_FAILED",
                "Website trả về nội dung rỗng.",
            )

        return _extract_article(
            html_content=html_content,
            requested_url=requested_url,
            final_url=final_url,
            http_status=status,
            content_type=content_type,
        )

    except CrawlError as exc:
        logger.info(
            "Article crawl rejected code=%s url=%s message=%s",
            exc.code,
            requested_url,
            exc.public_message,
        )
        return _error(exc.code, exc.public_message)
    except Exception:
        # Log stack trace ở server nhưng không trả exception nội bộ cho client.
        logger.exception("Unexpected article crawl error url=%s", requested_url)
        return _error(
            "UNEXPECTED_ERROR",
            "Không thể xử lý bài báo này. Vui lòng thử URL khác.",
        )
```

### Vì sao dùng `bare_extraction()`?

- `extract()` phù hợp khi chỉ cần một chuỗi TXT/JSON/Markdown hoàn chỉnh.
- `bare_extraction()` trả `Document`, giúp code đọc text, title, author, date,
  hostname, sitename và fingerprint mà không parse một JSON string trung gian.
- `.as_dict()` là API hiện hành; không dùng `bare_extraction(as_dict=True)` vì
  cách đó đã được đánh dấu deprecated.

### Vì sao vẫn dùng `to_markdown()`?

Template `detail.html` hiện render `original_text|linebreaks`, không dùng Markdown
renderer. Giữ `to_markdown()` giúp output mới gần giống output cũ và giảm thay
đổi giao diện. Nếu sau này frontend render Markdown thật, có thể dùng:

```python
from trafilatura import extract

markdown = extract(
    html_content,
    url=final_url,
    output_format="markdown",
    include_comments=False,
    include_tables=False,
)
```

Không nên đổi sang Markdown thật trước khi template có Markdown renderer an toàn.

## 7. Mở rộng MongoDB Pydantic schema

Trong `ReadAndQues/articles/models.py`, thêm import:

```python
from typing import Any, Dict, List, Optional
```

Sau trường `image_urls`, thêm vào `ArticleMongoModel`:

```python
canonical_url: Optional[str] = Field(
    default=None,
    description="Canonical/final URL after redirects",
)
author: Optional[str] = Field(default=None)
published_at: Optional[datetime] = Field(default=None)
language: Optional[str] = Field(default="en")
word_count: int = Field(default=0, ge=0)
crawl_metadata: Dict[str, Any] = Field(default_factory=dict)
```

Đây là Pydantic schema cho MongoDB, không phải Django ORM model, nên không chạy
`makemigrations`. Các field đều có default để document cũ vẫn validate được.

## 8. Cập nhật `import_article_view()`

Trong `ReadAndQues/articles/views.py`, mở rộng `pending_document`:

```python
pending_document = {
    "url": url,
    "canonical_url": crawl_res.get("canonical_url") or url,
    "title": crawl_res.get("title", ""),
    "original_text": crawl_res.get("content", ""),
    "source_name": crawl_res.get("source_name", "Unknown"),
    "author": crawl_res.get("author"),
    "published_at": crawl_res.get("published_at"),
    "language": crawl_res.get("language", "en"),
    "word_count": crawl_res.get("word_count", 0),
    "image_url": crawl_res.get("image_url"),
    "image_urls": crawl_res.get("image_urls") or [],
    "crawl_metadata": crawl_res.get("crawl_metadata") or {},
    "status": "pending",
    "user_id": request.user.id,
    "created_at": datetime.utcnow(),
}
```

Luồng AI không phải đổi vì vẫn nhận:

```python
crawl_res.get("content", "")
```

Nếu muốn dùng URL cuối cùng trong service và MongoDB, truyền canonical URL:

```python
article_url = crawl_res.get("canonical_url") or url

thread = threading.Thread(
    target=_run_article_generation,
    args=(article_url, crawl_res.get("content", ""), inserted_id),
    daemon=True,
)
```

Nên giữ `url` là URL người dùng nhập và lưu `canonical_url` riêng để audit được
redirect. Không nên ghi đè URL gốc.

## 9. Test crawler không gọi Internet

Tạo file:

```text
ReadAndQues/articles/tests/test_crawler.py
```

Nếu project chưa tổ chức `tests/` dạng package, tạo thêm
`ReadAndQues/articles/tests/__init__.py` và chuyển file `tests.py` hiện tại vào
package hoặc giữ test crawler trong `tests.py`. Không nên để đồng thời
`articles/tests.py` và `articles/tests/` vì import resolution dễ gây nhầm lẫn.

Ví dụ test bằng `SimpleTestCase`:

```python
from django.test import SimpleTestCase, override_settings

from articles.utils.crawler import (
    CrawlError,
    _extract_article,
    _extract_images,
    _validate_public_http_url,
)


SAMPLE_HTML = """
<!doctype html>
<html lang="en">
  <head>
    <title>Fallback HTML title</title>
    <meta property="og:title" content="Climate policy changes in Europe">
    <meta property="og:site_name" content="Example News">
    <meta property="og:image" content="/media/cover.jpg">
    <meta name="author" content="Jane Doe">
    <meta property="article:published_time" content="2026-07-20T08:30:00Z">
    <link rel="canonical" href="https://news.example/articles/climate-policy">
  </head>
  <body>
    <nav>Menu that must not become article text</nav>
    <article>
      <h1>Climate policy changes in Europe</h1>
      <p>European governments announced a detailed climate policy package.</p>
      <p>The package contains funding, reporting, and implementation rules.</p>
      <p>This paragraph is repeated to make the fixture long enough for validation.</p>
      <p>This paragraph is repeated to make the fixture long enough for validation.</p>
      <p>This paragraph is repeated to make the fixture long enough for validation.</p>
      <img src="/media/chart.jpg" alt="Climate chart">
    </article>
    <footer>Privacy policy and cookie settings</footer>
  </body>
</html>
"""


@override_settings(
    ARTICLE_MIN_WORDS=20,
    ARTICLE_MAX_WORDS=1000,
    ARTICLE_MAX_IMAGES=20,
)
class TrafilaturaExtractionTests(SimpleTestCase):
    def test_extracts_text_metadata_and_images(self):
        result = _extract_article(
            html_content=SAMPLE_HTML,
            requested_url="https://news.example/start",
            final_url="https://news.example/articles/climate-policy",
            http_status=200,
            content_type="text/html; charset=utf-8",
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["title"], "Climate policy changes in Europe")
        self.assertEqual(result["source_name"], "Example News")
        self.assertEqual(result["author"], "Jane Doe")
        self.assertGreaterEqual(result["word_count"], 20)
        self.assertNotIn("Privacy policy", result["content"])
        self.assertEqual(
            result["image_url"],
            "https://news.example/media/cover.jpg",
        )
        self.assertIn(
            "https://news.example/media/chart.jpg",
            result["image_urls"],
        )

    def test_rejects_short_content(self):
        with self.settings(ARTICLE_MIN_WORDS=1000):
            with self.assertRaises(CrawlError) as context:
                _extract_article(
                    html_content=SAMPLE_HTML,
                    requested_url="https://news.example/start",
                    final_url="https://news.example/article",
                    http_status=200,
                    content_type="text/html",
                )

        self.assertEqual(context.exception.code, "CONTENT_TOO_SHORT")

    def test_image_urls_are_made_absolute_and_deduplicated(self):
        image_url, image_urls = _extract_images(
            SAMPLE_HTML,
            base_url="https://news.example/articles/page",
            limit=20,
        )

        self.assertEqual(image_url, "https://news.example/media/cover.jpg")
        self.assertEqual(len(image_urls), len(set(image_urls)))

    def test_rejects_localhost(self):
        with self.assertRaises(CrawlError) as context:
            _validate_public_http_url("http://127.0.0.1:8000/admin/")

        self.assertEqual(context.exception.code, "PRIVATE_ADDRESS")

    def test_rejects_file_scheme(self):
        with self.assertRaises(CrawlError) as context:
            _validate_public_http_url("file:///etc/passwd")

        self.assertEqual(context.exception.code, "INVALID_URL")
```

### Test network adapter bằng mock

Ngoài extraction test, cần một test xác nhận `crawl_article_content()` xử lý
response đúng nhưng không gọi mạng thật:

```python
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from articles.utils.crawler import crawl_article_content


@override_settings(
    ARTICLE_MIN_WORDS=20,
    ARTICLE_MAX_WORDS=1000,
    ARTICLE_MAX_IMAGES=20,
)
class TrafilaturaDownloadAdapterTests(SimpleTestCase):
    @patch("articles.utils.crawler._validate_public_http_url")
    @patch("articles.utils.crawler.fetch_response")
    def test_crawl_uses_final_redirect_url(self, fetch_mock, validate_mock):
        fetch_mock.return_value = SimpleNamespace(
            status=200,
            url="https://news.example/final-article",
            headers={"content-type": "text/html; charset=utf-8"},
            html=SAMPLE_HTML,
            data=SAMPLE_HTML.encode(),
        )

        result = crawl_article_content("https://news.example/short-url")

        self.assertTrue(result["success"])
        self.assertEqual(
            result["crawl_metadata"]["final_url"],
            "https://news.example/final-article",
        )
        self.assertEqual(validate_mock.call_count, 2)
```

## 10. Chạy kiểm tra

Từ repository root:

```bash
uv sync
cd ReadAndQues
uv run python manage.py check
uv run python manage.py test articles
```

Test thủ công một URL không đi qua UI:

```bash
cd ReadAndQues
uv run python manage.py shell
```

Trong Django shell:

```python
from pprint import pprint
from articles.utils.crawler import crawl_article_content

result = crawl_article_content("https://example-news-site/article-url")
pprint(result)
```

Kiểm tra tối thiểu:

```python
assert result["success"] is True
assert result["title"]
assert result["content"]
assert result["word_count"] >= 120
assert result["crawl_metadata"]["crawler"] == "trafilatura"
```

## 11. Tập URL kiểm thử trước khi rollout

Không đánh giá crawler chỉ bằng một website. Chuẩn bị khoảng 20–50 URL gồm:

- Bài báo thông thường có `<article>` rõ ràng.
- Website dùng nhiều boilerplate/menu.
- URL redirect hoặc URL rút gọn.
- Bài có Open Graph image.
- Bài chỉ có lazy-loaded image (`data-src`, `srcset`).
- Bài không có tác giả/ngày xuất bản.
- Trang trả 403, 404, 429 và 500.
- Trang cần JavaScript mới có nội dung.
- URL PDF, ảnh hoặc JSON để xác nhận bị từ chối.
- URL localhost/private IP để xác nhận SSRF guard hoạt động.
- Bài rất ngắn và bài cực dài.

So sánh crawler cũ và mới theo các metric:

| Metric | Cách đo |
| --- | --- |
| Extraction success rate | Tỷ lệ URL có title + đủ text |
| Boilerplate rate | Menu/footer/cookie text còn sót |
| Text completeness | Đoạn đầu/cuối bài có bị mất không |
| Metadata coverage | Tỷ lệ có author/date/source/canonical URL |
| Image coverage | Tỷ lệ có ảnh đại diện hợp lệ |
| Latency p50/p95 | Thời gian download + extraction |
| AI success rate | Tỷ lệ LangGraph tạo được final exam |

## 12. Rollout an toàn

### Giai đoạn 1: chạy Trafilatura làm mặc định

Giữ public contract cũ, deploy crawler mới và ghi log:

```text
crawler=trafilatura
error_code=...
hostname=...
duration_ms=...
word_count=...
```

Không log toàn bộ nội dung bài báo hoặc exception nhạy cảm ra client.

### Giai đoạn 2: theo dõi

Theo dõi ít nhất:

- Tỷ lệ `DOWNLOAD_FAILED`.
- Tỷ lệ `EXTRACTION_FAILED`.
- Tỷ lệ bài dưới 120 từ.
- Thời gian crawler.
- Tỷ lệ AI pipeline thất bại sau khi crawler thành công.

### Giai đoạn 3: gỡ newspaper3k

Khi Trafilatura ổn định:

1. Xóa import `newspaper.Article`.
2. Xóa helper `_extract_images(article: NewspaperArticle)` cũ.
3. Chạy `uv remove newspaper3k`.
4. Cập nhật `requirements.txt` và `uv.lock`.
5. Chạy lại toàn bộ test.

## 13. Lưu ý bảo mật và vận hành

### SSRF

Kiểm tra DNS trong code là lớp bảo vệ cơ bản nhưng chưa loại bỏ hoàn toàn DNS
rebinding: hostname có thể đổi IP giữa lúc kiểm tra và lúc Trafilatura kết nối.
Môi trường production nên có thêm network egress policy/firewall chặn:

- `127.0.0.0/8`
- `10.0.0.0/8`
- `172.16.0.0/12`
- `192.168.0.0/16`
- `169.254.0.0/16`, đặc biệt metadata endpoints
- IPv6 loopback, link-local, unique-local và reserved ranges

### Robots.txt và điều khoản website

Trafilatura là công cụ extraction, không tự biến mọi nội dung thành dữ liệu được
phép sử dụng. Cần tôn trọng robots.txt, điều khoản của nguồn, copyright và giới
hạn tần suất. Nếu crawl hàng loạt, dùng hàng đợi có throttling theo domain thay vì
tạo request không giới hạn.

### Website render bằng JavaScript

Trafilatura xử lý HTML mà server trả về; nó không phải trình duyệt headless. Nếu
nội dung chỉ xuất hiện sau khi JavaScript chạy, crawler có thể trả rỗng. Không tự
động thêm Playwright làm fallback vào request web vì chi phí và bề mặt tấn công
lớn hơn. Nếu thật sự cần, triển khai renderer thành service/job riêng với giới hạn
tài nguyên chặt chẽ.

### Background job

Crawler hiện chạy đồng bộ trước khi tạo daemon thread, nên người dùng vẫn phải chờ
download/extraction hoàn tất trong request POST. Khi lưu lượng tăng, nên chuyển cả
crawl và LangGraph sang Celery/RQ/Dramatiq, trả job ID sớm và cập nhật trạng thái:

```text
queued -> crawling -> generating -> completed/failed
```

### Dữ liệu ảnh

Implementation chỉ lưu hotlink URL, không tải ảnh về. Hotlink có thể hết hạn,
chặn referrer hoặc thay đổi nội dung. Nếu ảnh là dữ liệu quan trọng, cần pipeline
riêng để kiểm tra content-type/size rồi upload sang object storage. Không tải ảnh
trực tiếp trong request import.

## 14. Definition of Done

Hoàn thành thay Trafilatura khi đáp ứng tất cả điều kiện:

- [ ] `trafilatura` có trong `pyproject.toml` và lockfile.
- [ ] `crawl_article_content()` không còn dùng `newspaper3k`.
- [ ] Contract cũ `title/content/source_name/image_url/image_urls` vẫn hoạt động.
- [ ] Có canonical URL, author, published date, language và word count.
- [ ] MongoDB schema chấp nhận cả document mới lẫn document cũ.
- [ ] URL đầu vào và URL sau redirect đều được kiểm tra.
- [ ] Không trả exception nội bộ ra client.
- [ ] Test extraction không gọi Internet.
- [ ] Test download adapter dùng mock.
- [ ] `manage.py check` thành công.
- [ ] Test `accounts` và `articles` thành công.
- [ ] Đã thử trên tập URL nhiều nguồn.
- [ ] Có log error code, hostname, latency và word count.
- [ ] Chỉ gỡ `newspaper3k` sau khi rollout Trafilatura ổn định.

