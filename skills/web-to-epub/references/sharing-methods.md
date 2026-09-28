# Sharing EPUBs to Mobile

Methods for getting converted EPUBs onto mobile devices.

## Telegram Bot (Recommended)

Set up a bot that accepts URLs and returns EPUB files.

### Setup

1. Create bot via @BotFather on Telegram
2. Get token (format: `123456:ABC-DEF...`)
3. Install `python-telegram-bot`:
   ```bash
   pip install python-telegram-bot
   ```
4. Run the bot script (see `scripts/telegram_bot.py` for template)

### Bot Features
- Accepts any URL (Substack, YouTube, web articles)
- Auto-detects source type
- Converts to EPUB and sends file back
- Works on mobile — just send URL to the bot

### Running

```bash
python telegram_bot.py
```

Run in background. The bot polls Telegram for new messages.

## Local HTTP Server (Same WiFi)

For instant access on mobile without cloud:

```bash
cd F:/Articles && python -m http.server 8080
```

Then open `http://YOUR_IP:8080` on mobile browser. Tap any EPUB to download.

## Cloud Storage

- **Google Drive**: Upload once, share link
- **Telegram Saved Messages**: Send to yourself, instant on mobile
- **WhatsApp**: Send to "Saved Messages" or yourself

## Notion (with workaround)

Notion free plan blocks multipart uploads. Workaround:

1. Upload EPUB to external hosting:
   ```bash
   curl -F "file=@article.epub" https://tmpfiles.org/api/v1/upload
   ```
2. Add as external file block to Notion page:
   ```json
   {"type": "file", "file": {"type": "external", "external": {"url": "https://tmpfiles.org/.../file.epub"}}}
   ```

This works on all plans and platforms.