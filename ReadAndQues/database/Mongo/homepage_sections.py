import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from database.Mongo.connection import get_collection

logger = logging.getLogger(__name__)


def update_section_data(section_id: str, data: list, expires_in_hours: int = 24) -> bool:
    now = datetime.now(timezone.utc)
    doc = {
        "section_id": section_id,
        "data": data,
        "updated_at": now,
        "expires_at": now + timedelta(hours=expires_in_hours),
    }
    result = get_collection("homepage_sections").update_one(
        {"section_id": section_id},
        {"$set": doc},
        upsert=True,
    )
    return result.acknowledged


def get_section_data(section_id: str) -> Optional[list]:
    doc = get_collection("homepage_sections").find_one({"section_id": section_id})
    if doc and doc.get("expires_at", datetime.min.replace(tzinfo=timezone.utc)) > datetime.now(timezone.utc):
        return doc.get("data", [])
    return None
