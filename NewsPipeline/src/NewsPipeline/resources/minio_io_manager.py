"""
NewsPipeline/resources/minio_io_manager.py — MinIO S3 Resource and IO Manager for HTML document storage.
"""

import io
import logging
import os
from typing import Any

from dagster import ConfigurableIOManager, ConfigurableResource, InputContext, OutputContext
from dotenv import find_dotenv, load_dotenv
from minio import Minio

load_dotenv(find_dotenv(usecwd=True))

logger = logging.getLogger(__name__)


def get_minio_client(
    endpoint: str | None = None,
    access_key: str | None = None,
    secret_key: str | None = None,
    secure: bool | None = None,
) -> Minio:
    """
    Construct MinIO client:
    Tries configured endpoint (e.g. 'minio:9000').
    If unreachable, falls back to 'localhost:9000' for local execution.
    """
    target_endpoint = endpoint or os.getenv("MINIO_ENDPOINT", "minio:9000")
    target_access_key = access_key or os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    target_secret_key = secret_key or os.getenv("MINIO_SECRET_KEY", "minioadmin")
    target_secure = secure if secure is not None else (os.getenv("MINIO_SECURE", "false").lower() == "true")

    client = Minio(
        endpoint=target_endpoint,
        access_key=target_access_key,
        secret_key=target_secret_key,
        secure=target_secure,
    )

    try:
        client.list_buckets()
        return client
    except Exception as e:
        logger.debug(f"MinIO primary connection to {target_endpoint} failed ({e}), trying localhost:9000...")
        if "minio:" in target_endpoint:
            fallback_endpoint = target_endpoint.replace("minio:", "localhost:")
            fallback_client = Minio(
                endpoint=fallback_endpoint,
                access_key=target_access_key,
                secret_key=target_secret_key,
                secure=target_secure,
            )
            try:
                fallback_client.list_buckets()
                logger.info(f"Connected to MinIO on {fallback_endpoint}.")
                return fallback_client
            except Exception:
                pass
        return client


class MinIOResource(ConfigurableResource):
    """
    Resource for storing and retrieving raw HTML and structured JSON documents in MinIO S3.
    Buckets:
      - 'raw-html': raw crawled HTML files (<date>/<article_id>.html)
      - 'silver-cleaned': sanitized article JSON files (<date>/<article_id>.json)
      - 'gold-content': curated gold article JSON files (<date>/<article_id>.json)
    """

    endpoint: str = "minio:9000"
    access_key: str = "minioadmin"
    secret_key: str = "minioadmin"
    secure: bool = False
    bucket: str = "raw-html"
    silver_bucket: str = "silver-cleaned"
    gold_bucket: str = "gold-content"

    def get_client(self) -> Minio:
        return get_minio_client(
            endpoint=self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure,
        )

    def ensure_bucket(self, bucket_name: str | None = None) -> None:
        target_bucket = bucket_name or self.bucket
        client = self.get_client()
        try:
            if not client.bucket_exists(target_bucket):
                client.make_bucket(target_bucket)
                logger.info(f"MinIOResource: Created bucket '{target_bucket}'.")
        except Exception as e:
            logger.debug(f"MinIOResource: Bucket check notice for '{target_bucket}': {e}")

    def save_html(self, partition_date: str, article_id: str, html_str: str) -> str:
        """Save a single raw HTML document to MinIO under date directory."""
        self.ensure_bucket(self.bucket)
        client = self.get_client()
        key = f"{partition_date}/{article_id}.html"
        raw_bytes = html_str.encode("utf-8")

        client.put_object(
            bucket_name=self.bucket,
            object_name=key,
            data=io.BytesIO(raw_bytes),
            length=len(raw_bytes),
            content_type="text/html; charset=utf-8",
        )
        return key

    def read_html(self, partition_date: str, article_id: str) -> str:
        """Read a single raw HTML document from MinIO."""
        client = self.get_client()
        key = f"{partition_date}/{article_id}.html"
        response = client.get_object(self.bucket, key)
        content = response.read().decode("utf-8")
        response.close()
        response.release_conn()
        return content

    def save_silver_article(self, partition_date: str, article_id: str, doc_dict: dict[str, Any]) -> str:
        """Save a sanitized clean article JSON document to MinIO 'silver-cleaned' bucket."""
        import json
        self.ensure_bucket(self.silver_bucket)
        client = self.get_client()
        key = f"{partition_date}/{article_id}.json"
        raw_bytes = json.dumps(doc_dict, ensure_ascii=False, default=str).encode("utf-8")

        client.put_object(
            bucket_name=self.silver_bucket,
            object_name=key,
            data=io.BytesIO(raw_bytes),
            length=len(raw_bytes),
            content_type="application/json; charset=utf-8",
        )
        return key

    def read_silver_article(self, partition_date: str, article_id: str) -> dict[str, Any]:
        """Read a sanitized clean article JSON document from MinIO 'silver-cleaned' bucket."""
        import json
        client = self.get_client()
        key = f"{partition_date}/{article_id}.json"
        response = client.get_object(self.silver_bucket, key)
        content = response.read().decode("utf-8")
        response.close()
        response.release_conn()
        return json.loads(content)

    def save_gold_article(self, partition_date: str, article_id: str, doc_dict: dict[str, Any]) -> str:
        """Save a curated gold article JSON document to MinIO 'gold-content' bucket."""
        import json
        self.ensure_bucket(self.gold_bucket)
        client = self.get_client()
        key = f"{partition_date}/{article_id}.json"
        raw_bytes = json.dumps(doc_dict, ensure_ascii=False, default=str).encode("utf-8")

        client.put_object(
            bucket_name=self.gold_bucket,
            object_name=key,
            data=io.BytesIO(raw_bytes),
            length=len(raw_bytes),
            content_type="application/json; charset=utf-8",
        )
        return key


class MinIOIOManager(ConfigurableIOManager):
    """
    MinIO IO Manager for Dagster asset IO bindings.
    """

    endpoint: str = "minio:9000"
    access_key: str = "minioadmin"
    secret_key: str = "minioadmin"
    secure: bool = False
    bucket: str = "raw-html"

    def handle_output(self, context: OutputContext, obj: Any) -> None:
        pass

    def load_input(self, context: InputContext) -> Any:
        return []
