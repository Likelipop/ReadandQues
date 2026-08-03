import json
import logging
from typing import Dict, Any, Optional
from io import BytesIO
from database.Minio.connection import client, BRONZE_BUCKET, SILVER_BUCKET
import urllib3

logger = logging.getLogger(__name__)

def save_to_minio(bucket_name: str, object_name: str, data: bytes, content_type: str = "application/octet-stream"):
    try:
        data_stream = BytesIO(data)
        client.put_object(
            bucket_name=bucket_name,
            object_name=object_name,
            data=data_stream,
            length=len(data),
            content_type=content_type
        )
        return True
    except Exception as e:
        logger.error(f"Error saving {object_name} to {bucket_name}: {e}")
        return False

def save_bronze_html(object_name: str, html_content: str) -> bool:
    data = html_content.encode('utf-8')
    return save_to_minio(BRONZE_BUCKET, object_name, data, "text/html")

def save_bronze_json(object_name: str, json_data: Dict[str, Any]) -> bool:
    data = json.dumps(json_data, ensure_ascii=False).encode('utf-8')
    return save_to_minio(BRONZE_BUCKET, object_name, data, "application/json")

def save_silver_json(object_name: str, json_data: Dict[str, Any]) -> bool:
    data = json.dumps(json_data, ensure_ascii=False).encode('utf-8')
    return save_to_minio(SILVER_BUCKET, object_name, data, "application/json")

def read_from_minio(bucket_name: str, object_name: str) -> Optional[bytes]:
    try:
        response = client.get_object(bucket_name, object_name)
        data = response.read()
        response.close()
        response.release_conn()
        return data
    except urllib3.exceptions.ResponseError as err:
        logger.error(f"Response error fetching {object_name} from {bucket_name}: {err}")
    except Exception as e:
        logger.error(f"Error reading {object_name} from {bucket_name}: {e}")
    return None

def read_json_from_minio(bucket_name: str, object_name: str) -> Optional[Dict[str, Any]]:
    data = read_from_minio(bucket_name, object_name)
    if data:
        return json.loads(data.decode('utf-8'))
    return None

def list_objects(bucket_name: str, prefix: str = "", recursive: bool = True):
    try:
        objects = client.list_objects(bucket_name, prefix=prefix, recursive=recursive)
        return [obj.object_name for obj in objects]
    except Exception as e:
        logger.error(f"Error listing objects in {bucket_name} with prefix {prefix}: {e}")
        return []
