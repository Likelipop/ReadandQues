"""
worker_service/data_pipeline/init_db.py — Initialize MongoDB database and collections.

Creates the 'articles' database with Bronze, Silver, Gold, Logs, and Attempts collections.
Sets up indexes for efficient querying across the pipeline.

Usage:
    python -m worker_service.data_pipeline.init_db
"""

from worker_service.database.Mongo.connection import db
from worker_service.database.Mongo.crud import init_mongo_indexes


def main():
    print(f"\n🔧 Initializing MongoDB database: '{db.name}'")
    print(f"   URI: {db.client.address}\n")
    init_mongo_indexes()
    print(f"\n✅ Database '{db.name}' initialization complete.\n")


if __name__ == "__main__":
    main()
