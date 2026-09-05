import asyncio
import logging
import os
from datetime import datetime, timezone

from pyrogram import filters

log = logging.getLogger("autofilter.indexer")


def _channels():
    out = set()
    for value in os.getenv("INDEX_CHANNELS", "").split(","):
        value = value.strip()
        if value:
            try:
                out.add(int(value))
            except ValueError:
                pass
    return out


def register_indexer(app, db):
    allowed = _channels()
    queue = asyncio.Queue(maxsize=int(os.getenv("INDEX_QUEUE_SIZE", "1000")))
    workers = int(os.getenv("INDEX_WORKERS", "4"))

    async def producer(_, message):
        if allowed and message.chat.id not in allowed:
            return
        media = message.document or message.video or message.audio
        if not media or not getattr(media, "file_unique_id", None):
            return
        item = {
            "file_unique_id": media.file_unique_id,
            "file_id": media.file_id,
            "name": getattr(media, "file_name", None) or "unnamed_file",
            "size": getattr(media, "file_size", 0) or 0,
            "chat_id": message.chat.id,
            "message_id": message.id,
            "mime_type": getattr(media, "mime_type", None),
            "file_type": message.media.value if message.media else None,
            "caption": message.caption or None,
            "created_at": datetime.now(timezone.utc),
        }
        try:
            queue.put_nowait(item)
        except asyncio.QueueFull:
            log.warning("Index queue full; dropping one event to keep bot responsive")

    async def worker(n):
        while True:
            item = await queue.get()
            try:
                await db.add_file(item)
            except Exception:
                log.exception("Indexer worker %s failed", n)
            finally:
                queue.task_done()

    for i in range(workers):
        asyncio.create_task(worker(i + 1))

    app.add_handler(__import__("pyrogram").handlers.MessageHandler(
        producer,
        filters.channel & (filters.document | filters.video | filters.audio),
    ))
