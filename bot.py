import asyncio
import logging
import os
import time

from aiohttp import web
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from database import FileDB
from indexer import register_indexer
from search import register_search
from admin import register_admin

load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
log = logging.getLogger("autofilter")

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
MONGO_URI = os.environ["MONGO_URI"]
DB_NAME = os.getenv("DATABASE_NAME", "autofilter")
PORT = int(os.getenv("PORT", "8080"))
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

START_TEXT = os.getenv("START_TEXT", "👋 Welcome! Send a movie/file name to search.")
HELP_TEXT = os.getenv("HELP_TEXT", "🔎 Send a name to search files.\n/ping — bot latency\n/stats — admin statistics")

# Keep Telegram handlers responsive; DB work is async and indexing is queued.
app = Client(
    "advanced_autofilter_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=int(os.getenv("PYROGRAM_WORKERS", "32")),
    sleep_threshold=20,
)

db = FileDB(MONGO_URI, DB_NAME)

register_indexer(app, db)
register_search(app, db)
register_admin(app, db)

@app.on_message(filters.private & filters.command("start"))
async def start(_, message: Message):
    await message.reply_text(
        START_TEXT,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔎 Search", switch_inline_query_current_chat="")],
            [InlineKeyboardButton("ℹ️ Help", callback_data="help")],
        ]),
    )

@app.on_callback_query(filters.regex("^help$"))
async def help_callback(_, query):
    await query.answer()
    await query.message.edit_text(HELP_TEXT)

@app.on_message(filters.private & filters.command("help"))
async def help_command(_, message: Message):
    await message.reply_text(HELP_TEXT)

@app.on_message(filters.private & filters.command("ping"))
async def ping(_, message: Message):
    started = time.perf_counter()
    sent = await message.reply_text("🏓 Checking...")
    ms = (time.perf_counter() - started) * 1000
    try:
        db_ms = await db.ping()
    except Exception:
        db_ms = -1
    text = f"🏓 <b>Pong!</b>\nTelegram: <code>{ms:.0f} ms</code>\nMongoDB: <code>{db_ms:.0f} ms</code>"
    await sent.edit_text(text)

@app.on_message(filters.private & filters.command("id"))
async def show_id(_, message: Message):
    await message.reply_text(f"User ID: <code>{message.from_user.id}</code>\nChat ID: <code>{message.chat.id}</code>")

async def health(request):
    return web.json_response({"status": "ok", "service": "autofilter"})

async def start_health_server():
    server = web.Application()
    server.router.add_get("/", health)
    server.router.add_get("/health", health)
    runner = web.AppRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    log.info("Health server listening on %s", PORT)
    return runner

async def main():
    await db.ensure_indexes()
    await app.start()
    runner = await start_health_server()
    log.info("Bot started")
    try:
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()
        await app.stop()
        await db.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
