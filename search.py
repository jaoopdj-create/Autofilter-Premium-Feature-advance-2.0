import asyncio
from pyrogram import filters
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

PAGE_SIZE = 10


def register_search(app, db):
    async def show_results(message, query, offset=0):
        results, total = await db.search(query, PAGE_SIZE, offset)
        if not results:
            await message.reply_text("❌ No matching files found.")
            return
        buttons = []
        for item in results:
            name = item.get("name", "File")[:55]
            buttons.append([InlineKeyboardButton(name, callback_data=f"file:{item['chat_id']}:{item['message_id']}")])
        nav = []
        if offset > 0:
            nav.append(InlineKeyboardButton("⬅️", callback_data=f"page:{offset-PAGE_SIZE}:{query[:35]}"))
        if offset + PAGE_SIZE < total:
            nav.append(InlineKeyboardButton("➡️", callback_data=f"page:{offset+PAGE_SIZE}:{query[:35]}"))
        if nav:
            buttons.append(nav)
        await message.reply_text(f"🔎 <b>{total}</b> result(s) for <code>{query}</code>", reply_markup=InlineKeyboardMarkup(buttons))

    @app.on_message(filters.private & filters.command("search"))
    async def search_command(_, message):
        if len(message.command) < 2:
            return await message.reply_text("Usage: /search filename")
        await show_results(message, " ".join(message.command[1:]))

    @app.on_message(filters.private & filters.text & ~filters.command(["start", "help", "search", "ping", "stats", "id"]))
    async def plain_search(_, message):
        if message.text and len(message.text.strip()) >= 2:
            await show_results(message, message.text.strip())

    @app.on_callback_query(filters.regex(r"^file:-?\d+:\d+$"))
    async def send_file(_, query):
        _, chat_id, message_id = query.data.split(":")
        await query.answer("📤 Sending file...")
        try:
            await app.copy_message(query.from_user.id, int(chat_id), int(message_id))
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await app.copy_message(query.from_user.id, int(chat_id), int(message_id))
        except Exception:
            await query.message.reply_text("⚠️ File is currently unavailable.")

    @app.on_callback_query(filters.regex(r"^page:-?\d+:.+$"))
    async def page(_, query):
        _, offset, q = query.data.split(":", 2)
        offset = max(0, int(offset))
        results, total = await db.search(q, PAGE_SIZE, offset)
        if not results:
            return await query.answer("No more results", show_alert=True)
        buttons = [[InlineKeyboardButton(x.get("name", "File")[:55], callback_data=f"file:{x['chat_id']}:{x['message_id']}")] for x in results]
        nav = []
        if offset > 0: nav.append(InlineKeyboardButton("⬅️", callback_data=f"page:{offset-PAGE_SIZE}:{q}"))
        if offset + PAGE_SIZE < total: nav.append(InlineKeyboardButton("➡️", callback_data=f"page:{offset+PAGE_SIZE}:{q}"))
        if nav: buttons.append(nav)
        await query.message.edit_reply_markup(InlineKeyboardMarkup(buttons))
        await query.answer()
