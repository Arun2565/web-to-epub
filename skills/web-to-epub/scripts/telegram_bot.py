#!/usr/bin/env python3
"""Telegram bot that converts URLs to EPUB files."""

import os
import re
import tempfile
import logging
from urllib.parse import urlparse

from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token - REPLACE WITH YOUR OWN
TOKEN = "YOUR_BOT_TOKEN_HERE"

# Supported URL patterns
SUBSTACK_PATTERNS = [
    r"https?://[^/]+\.substack\.com/p/",
    r"https?://lennysnewsletter\.com/p/",
]

YOUTUBE_PATTERNS = [
    r"https?://(?:www\.)?youtube\.com/watch",
    r"https?://youtu\.be/",
]


def detect_source_type(url: str) -> str:
    for pattern in SUBSTACK_PATTERNS:
        if re.match(pattern, url):
            return "substack"
    for pattern in YOUTUBE_PATTERNS:
        if re.match(pattern, url):
            return "youtube"
    return "web"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_text(
        f"Hi {user.first_name}! Send me any URL and I'll convert it to EPUB.\n\n"
        "Supported: Substack, YouTube, web articles\n"
        "Commands: /start /help /status"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Send me a URL to convert it to EPUB.\n"
        "Use /help for this help message."
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("✅ Bot is running! Send a URL to convert.")


async def convert_url_to_epub(url: str, output_path: str) -> dict:
    """Convert URL to EPUB. Returns metadata dict."""
    import ssl
    import urllib.request
    from bs4 import BeautifulSoup
    from ebooklib import epub

    source_type = detect_source_type(url)
    
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
        html = response.read().decode('utf-8')
    
    soup = BeautifulSoup(html, 'html.parser')
    
    title_tag = soup.find('title')
    title = title_tag.get_text(strip=True) if title_tag else "Article"
    
    article = soup.find('article')
    if not article:
        article = soup.find('main')
    if not article:
        article = soup.find(class_='content')
    if not article:
        article = soup.find('body')
    
    paragraphs = article.find_all('p') if article else []
    
    book = epub.EpubBook()
    book.set_identifier(url)
    book.set_title(title)
    book.set_language('en')
    
    style = '''
    body { font-family: Georgia, serif; line-height: 1.7; margin: 5%; color: #1a1a1a; }
    h1 { font-size: 1.5em; margin-bottom: 0.5em; }
    h2 { font-size: 1.3em; margin-top: 1.5em; margin-bottom: 0.5em; }
    p { margin: 0.8em 0; text-align: justify; }
    a { color: #0066cc; text-decoration: none; }
    '''
    
    nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css",
                             media_type="text/css", content=style)
    book.add_item(nav_css)
    
    title_page = epub.EpubHtml(title='Title Page', file_name='title_page.xhtml')
    title_page.content = f'''
    <html><head><title>{title}</title></head><body>
    <div style="text-align: center; margin-top: 30%;">
        <h1>{title}</h1>
        <p style="margin-top: 3em;"><a href="{url}">Original</a></p>
    </div>
    </body></html>
    '''
    book.add_item(title_page)
    
    if paragraphs:
        chapter = epub.EpubHtml(title='Content', file_name='chapter_1.xhtml')
        content = []
        for p in paragraphs:
            text = p.get_text(separator=' ', strip=True)
            if text:
                content.append(f'<p>{text}</p>')
        
        chapter.content = f'''
        <html><head><title>Content</title></head><body>
        {''.join(content)}
        </body></html>
        '''
        chapter.add_item(nav_css)
        book.add_item(chapter)
        book.toc = [(epub.Section('Content'), [chapter])]
        book.spine = ['nav', title_page, chapter]
    else:
        book.spine = ['nav', title_page]
    
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    
    epub.write_epub(output_path, book)
    
    return {
        'title': title,
        'source_type': source_type,
        'paragraphs': len(paragraphs) if paragraphs else 0,
    }


async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = update.message.text.strip()
    
    if not re.match(r'^https?://', url):
        await update.message.reply_text("Please send a valid URL.")
        return
    
    source_type = detect_source_type(url)
    status_message = await update.message.reply_text(
        f"🔄 Processing {source_type} URL..."
    )
    
    try:
        with tempfile.NamedTemporaryFile(suffix='.epub', delete=False) as tmp:
            tmp_path = tmp.name
        
        metadata = await convert_url_to_epub(url, tmp_path)
        
        with open(tmp_path, 'rb') as f:
            await update.message.reply_document(
                document=f,
                filename=f"{metadata['title'][:50]}.epub",
                caption=f"📚 {metadata['title']}\n🔗 {url}"
            )
        
        await status_message.delete()
        os.unlink(tmp_path)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await status_message.edit_text(f"❌ Error: {str(e)[:500]}")
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    if re.match(r'^https?://', text):
        await handle_url(update, context)
    else:
        await update.message.reply_text("Send a URL to convert to EPUB.")


def main() -> None:
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app.bot.set_my_commands([
        BotCommand("start", "Start the bot"),
        BotCommand("help", "Show help"),
        BotCommand("status", "Check status"),
    ])
    
    print("Bot is starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
