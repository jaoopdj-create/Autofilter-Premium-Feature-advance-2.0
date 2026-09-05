import re
import time
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING

class FileDB:
    def __init__(self, uri: str, database_name: str):
        self.client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000)
        self.db = self.client[database_name]
        self.files = self.db.files

    async def ensure_indexes(self):
        await self.files.create_index([("file_unique_id", ASCENDING)], unique=True, name="uniq_file")
        await self.files.create_index([("name", ASCENDING)], name="name_idx")
        await self.files.create_index([("created_at", DESCENDING)], name="created_idx")
        await self.files.create_index([("chat_id", ASCENDING), ("message_id", ASCENDING)], name="source_idx")

    async def ping(self):
        started = time.perf_counter()
        await self.db.command("ping")
        return (time.perf_counter() - started) * 1000

    async def add_file(self, data: dict):
        data["updated_at"] = datetime.now(timezone.utc)
        return await self.files.update_one(
            {"file_unique_id": data["file_unique_id"]},
            {"$set": data, "$setOnInsert": {"created_at": data.get("created_at", datetime.now(timezone.utc))}},
            upsert=True,
        )

    async def search(self, query: str, limit: int = 10, offset: int = 0):
        query = re.sub(r"\s+", " ", query.strip())
        if not query:
            return [], 0
        # Escape user input so search never becomes an arbitrary Mongo regex.
        pattern = re.escape(query).replace(r"\ ", r"[ ._\-]+")
        cursor = self.files.find(
            {"name": {"$regex": pattern, "$options": "i"}},
            {"chat_id": 1, "message_id": 1, "name": 1, "size": 1, "file_type": 1},
        ).sort("created_at", DESCENDING).skip(offset).limit(limit)
        results = await cursor.to_list(length=limit)
        total = await self.files.count_documents({"name": {"$regex": pattern, "$options": "i"}})
        return results, total

    async def count(self):
        return await self.files.estimated_document_count()

    async def close(self):
        self.client.close()
