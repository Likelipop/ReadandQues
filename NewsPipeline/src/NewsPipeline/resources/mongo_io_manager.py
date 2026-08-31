"""
NewsPipeline/resources/mongo_io_manager.py — MongoDB IO Manager for 1:1 asset-to-collection mapping.
"""

import logging
import os
from typing import Any

from dagster import ConfigurableIOManager, InputContext, OutputContext
from dotenv import find_dotenv, load_dotenv
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

load_dotenv(find_dotenv(usecwd=True))

logger = logging.getLogger(__name__)


def get_mongo_client(uri: str | None = None) -> MongoClient:
    """
    Connect to MongoDB:
    Tries the configured URI (e.g. 'mongo:27017' in Docker).
    If unreachable, automatically falls back to 'localhost:27017' for local execution.
    """
    target_uri = uri or os.getenv("MONGO_URI")
    if not target_uri:
        user = os.getenv("MONGO_INITDB_ROOT_USERNAME", "admin")
        pwd = os.getenv("MONGO_INITDB_ROOT_PASSWORD", "changeme")
        db_name = os.getenv("MONGO_INITDB_DATABASE", "articlesDB")
        target_uri = f"mongodb://{user}:{pwd}@mongo:27017/{db_name}?authSource=admin"

    try:
        client = MongoClient(target_uri, serverSelectionTimeoutMS=2000)
        client.admin.command("ping")
        return client
    except Exception as e:
        logger.debug(f"Mongo primary connection failed ({e}), attempting localhost fallback...")
        fallback_uri = target_uri.replace("@mongo:27017", "@localhost:27017").replace("@mongo", "@localhost")
        try:
            client = MongoClient(fallback_uri, serverSelectionTimeoutMS=2000)
            client.admin.command("ping")
            logger.info("Connected to MongoDB on localhost.")
            return client
        except Exception:
            return MongoClient(target_uri, serverSelectionTimeoutMS=5000)


class MongoIOManager(ConfigurableIOManager):
    """
    IO Manager that persists asset outputs to MongoDB collections.
    Derives collection name from the asset key string (e.g. bronze_links, gold_content).
    """

    mongo_uri: str = "mongodb://admin:changeme@mongo:27017/articlesDB?authSource=admin"

    def get_database(self) -> Database:
        uri = os.getenv("MONGO_URI", self.mongo_uri)
        client = get_mongo_client(uri)
        db_name = os.getenv("MONGO_DB_NAME") or os.getenv("MONGO_INITDB_DATABASE", "articlesDB")
        return client[db_name]

    def get_collection(self, collection_name: str) -> Collection:
        return self.get_database()[collection_name]

    def handle_output(self, context: OutputContext, obj: Any) -> None:
        """Upsert asset output documents into the corresponding MongoDB collection."""
        if obj is None:
            return

        collection_name = context.asset_key.to_user_string()
        col = self.get_collection(collection_name)

        docs = obj if isinstance(obj, list) else [obj]

        for doc in docs:
            if not isinstance(doc, dict):
                continue

            if "article_id" in doc:
                col.update_one({"article_id": doc["article_id"]}, {"$set": doc}, upsert=True)
            elif "url" in doc:
                col.update_one({"url": doc["url"]}, {"$set": doc}, upsert=True)
            else:
                col.insert_one(doc)

        logger.info(f"MongoIOManager: Upserted {len(docs)} documents into '{collection_name}'.")

    def load_input(self, context: InputContext) -> list[dict[str, Any]]:
        """
        Load input documents from MongoDB collection.
        If a partition key is present in the context, filters by partition_date or partition_key.
        """
        collection_name = context.asset_key.to_user_string()
        col = self.get_collection(collection_name)

        if context.has_partition_key:
            partition_key = context.partition_key
            filter_query = {"$or": [{"partition_date": partition_key}, {"partition_key": partition_key}]}
            docs = list(col.find(filter_query, {"_id": 0}))
            return docs

        return list(col.find({}, {"_id": 0}))
