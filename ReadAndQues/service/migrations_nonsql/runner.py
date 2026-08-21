import hashlib
import importlib.util
import logging
from datetime import UTC, datetime
from pathlib import Path

from service.infrastructure.mongo.connection import get_mongo_db

logger = logging.getLogger(__name__)

VERSIONS_DIR = Path(__file__).resolve().parent / "versions"


class NonSqlMigrationRunner:
    """
    Locked, checksummed migration runner for non-SQL datastores (MongoDB, MinIO, ChromaDB).
    """

    def __init__(self):
        self.db = get_mongo_db()
        self.migrations_coll = self.db["_migrations"]

    def _calculate_checksum(self, file_path: Path) -> str:
        content = file_path.read_bytes()
        return hashlib.sha256(content).hexdigest()

    def get_applied_migrations(self) -> dict:
        applied = {}
        for doc in self.migrations_coll.find():
            applied[doc["name"]] = doc
        return applied

    def run(self) -> list[str]:
        if not VERSIONS_DIR.exists():
            VERSIONS_DIR.mkdir(parents=True, exist_ok=True)
            return []

        migration_files = sorted(VERSIONS_DIR.glob("*.py"))
        applied_map = self.get_applied_migrations()
        executed = []

        for file_path in migration_files:
            name = file_path.name
            checksum = self._calculate_checksum(file_path)

            if name in applied_map:
                stored_checksum = applied_map[name].get("checksum")
                if stored_checksum and stored_checksum != checksum:
                    raise RuntimeError(
                        f"Checksum mismatch for applied migration '{name}'. "
                        f"Stored: {stored_checksum}, Current: {checksum}"
                    )
                continue

            logger.info(f"Applying non-SQL migration: {name}")

            spec = importlib.util.spec_from_file_location(name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if not hasattr(module, "apply"):
                raise AttributeError(f"Migration script '{name}' missing apply() function.")

            module.apply(self.db)

            record = {
                "name": name,
                "checksum": checksum,
                "applied_at": datetime.now(UTC),
            }
            self.migrations_coll.update_one({"name": name}, {"$set": record}, upsert=True)
            executed.append(name)
            logger.info(f"Successfully applied non-SQL migration: {name}")

        return executed
