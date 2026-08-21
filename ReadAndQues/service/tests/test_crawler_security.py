import unittest
from service.crawler.scraper import CrawlError, _validate_public_http_url, crawl_article_content


class CrawlerSecurityTestSuite(unittest.TestCase):
    """Security & SSRF Penetration Tests for Article Crawler."""

    def test_reject_localhost_and_loopback(self):
        loopback_urls = [
            "http://127.0.0.1:8000/secret",
            "http://127.0.0.1:27017",
            "http://localhost:9000",
            "http://localhost/admin",
            "http://[::1]/",
        ]
        for url in loopback_urls:
            with self.subTest(url=url):
                with self.assertRaises(CrawlError):
                    _validate_public_http_url(url)

    def test_reject_private_ip_ranges(self):
        private_urls = [
            "http://10.0.0.1/status",
            "http://10.255.255.255/metrics",
            "http://172.16.0.1/",
            "http://172.31.255.255/internal",
            "http://192.168.1.1/router",
            "http://192.168.0.100:8080/",
        ]
        for url in private_urls:
            with self.subTest(url=url):
                with self.assertRaises(CrawlError):
                    _validate_public_http_url(url)

    def test_reject_cloud_metadata_endpoints(self):
        metadata_urls = [
            "http://169.254.169.254/latest/meta-data/",
            "http://169.254.169.254/computeMetadata/v1/",
        ]
        for url in metadata_urls:
            with self.subTest(url=url):
                with self.assertRaises(CrawlError):
                    _validate_public_http_url(url)

    def test_reject_embedded_credentials(self):
        credential_urls = [
            "http://admin:secret123@example.com/page",
            "https://user:password@example.com/",
        ]
        for url in credential_urls:
            with self.subTest(url=url):
                with self.assertRaises(CrawlError):
                    _validate_public_http_url(url)

    def test_reject_non_http_schemes(self):
        non_http_urls = [
            "file:///etc/passwd",
            "gopher://127.0.0.1:70/",
            "ftp://ftp.example.com/file.txt",
            "javascript:alert(1)",
        ]
        for url in non_http_urls:
            with self.subTest(url=url):
                with self.assertRaises(CrawlError):
                    _validate_public_http_url(url)

    def test_crawl_article_content_returns_structured_error_on_ssrf(self):
        result = crawl_article_content("http://127.0.0.1:5000/internal")
        self.assertFalse(result.get("success"))
        self.assertIn("error", result)
