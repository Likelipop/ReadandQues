import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from database.Mongo.connection import homepage_sections_collection

logger = logging.getLogger(__name__)

def update_section_data(section_id: str, data: list, expires_in_hours: int = 24) -> bool:
    try:
        doc = {
            "section_id": section_id,
            "data": data,
            "updated_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(hours=expires_in_hours)
        }
        
        homepage_sections_collection.update_one(
            {"section_id": section_id},
            {"$set": doc},
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"Failed to update homepage section {section_id}: {e}")
        return False

def get_section_data(section_id: str) -> Optional[list]:
    try:
        doc = homepage_sections_collection.find_one({"section_id": section_id})
        if doc and doc.get("expires_at", datetime.min) > datetime.utcnow():
            return doc.get("data", [])
        return None
    except Exception as e:
        logger.error(f"Failed to get homepage section {section_id}: {e}")
        return None
