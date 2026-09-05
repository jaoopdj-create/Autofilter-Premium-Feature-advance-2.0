import os
from pyrogram import filters


def register_admin(app, db):
    owner = int(os.getenv("OWNER_ID", "0"))

    @app.on_message(filters.private & filters.command("stats") & filters.user(owner))
    async def stats(_, message):
        await message.reply_text(f"📊 Indexed files: <code>{await db.count()}</code>")
