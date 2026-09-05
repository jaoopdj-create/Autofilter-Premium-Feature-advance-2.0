# Advanced AutoFilter Bot

A responsive Pyrogram + MongoDB file indexer/search bot for content you own or are authorized to distribute.

## Improvements
- Async MongoDB access (no blocking DB calls in Telegram handlers)
- Background indexing queue so channel posts do not block the bot
- Configurable index workers and Pyrogram workers
- Safe escaped search queries
- Pagination for search results
- Duplicate protection using Telegram `file_unique_id`
- `/ping` reports Telegram + MongoDB latency
- `/health` HTTP endpoint for deployment health checks
- FloodWait-aware file delivery
- `.env` customization for messages and performance

## Setup
1. Copy `.env.example` to `.env` and fill credentials.
2. Install: `pip install -r requirements.txt`
3. Run: `python bot.py`
4. Make the bot an admin in channels you are authorized to index and set their IDs in `INDEX_CHANNELS`.

The bot stores Telegram file/message references and metadata in MongoDB; it does not need to download the entire file to the bot server just to index it.
