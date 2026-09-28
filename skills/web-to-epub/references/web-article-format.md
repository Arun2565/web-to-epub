# Web Article to EPUB Conversion

Convert web articles (Substack, blog posts, HuggingFace blog, etc.) to EPUB using `web_extract`.

## Workflow

### 1. Extract Content

Use `web_extract` tool with the article URL:

```
web_extract(urls=[url], char_limit=50000)
```

Returns markdown/text content.

### 2. HuggingFace Blog Cleanup

HuggingFace blog posts (`huggingface.co/blog/`) inject platform-specific chrome. Strip these patterns:

- **Avatar images**: Lines matching `- [![](url)](link "author")` — remove
- **Upvote buttons**: Multi-line `[Upvote \\n\\n count](link)` blocks — remove
- **Follow buttons**: `[Name\\nusername\\n\\nFollow](link)` — remove
- **Back to Articles**: Top-of-page link — remove
- **More Articles from our Blog** / **More from this author**: Remove section and everything after
- **Spaces mentioned in this article**: Remove section and everything after
- **Community section**: Remove `### Community` and everything after
- **Comment UI elements**: `EditPreview`, `Upload images, audio, and videos...`, `Tap or paste here to upload images`, `Comment`

**Key rule**: Find the first `# ` heading (article title) and first `## ` heading (first section) to bound the content. Stop at the first cross-promotional or comment marker.

### 3. Parse Headings into Chapters

Parse the extracted text line by line. Headings start with `#`, `##`, or `###`:

```python
import re

def parse_article_to_chapters(text):
    chapters = []
    lines = text.strip().split('\n')
    current_title = None
    current_content = []
    
    for line in lines:
        heading_match = re.match(r'^#{1,3}\s+(.+)', line)
        if heading_match:
            if current_title and current_content:
                chapters.append((current_title, '\n'.join(current_content)))
            current_title = heading_match.group(1).strip()
            current_content = []
            continue
        if line.strip():
            current_content.append(line)
    
    if current_title and current_content:
        chapters.append((current_title, '\n'.join(current_content)))
    
    return chapters
```

### 3. Extract and Download Images

Identify image URLs from the extracted content or by parsing the original HTML. Download with `urllib.request`:

```python
import urllib.request
import ssl
import os

def download_images(image_urls, output_dir):
    img_dir = os.path.join(output_dir, 'images')
    os.makedirs(img_dir, exist_ok=True)
    
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    downloaded = {}
    for name, url in image_urls.items():
        filename = f"{name}.png"
        filepath = os.path.join(img_dir, filename)
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, context=ssl_context, timeout=30) as response:
                with open(filepath, 'wb') as f:
                    f.write(response.read())
            downloaded[name] = filepath
        except Exception as e:
            print(f"Failed {filename}: {e}")
    return downloaded
```

### 4. Build EPUB

Use `ebooklib` to create the EPUB with chapters and embedded images:

```python
from ebooklib import epub

book = epub.EpubBook()
book.set_identifier('unique-id')
book.set_title('Article Title')
book.set_language('en')
book.add_author('Author Name')

# Add CSS, title page, chapters, images
# See SKILL.md for CSS styling
```

## Pitfalls

- **NEVER manually define or invent chapter headings** — always extract headings from the source (web_extract markdown or HTML). The user will reject output with made-up section names. Parse `##` headings from web_extract output, or `<h2>` tags from HTML — never hardcode them.
- **Don't parse HTML when `web_extract` works** — the tool returns clean text; regex on headings is simpler than BeautifulSoup. Use web_extract as the primary source.
- **Skip navigation chrome** — Substack extracts include "Subscribe", "Share", author avatars, and related posts. Filter these out by stopping at sections like "How You Can Support" or "Related Posts".
- **Download images separately** — `web_extract` returns image URLs but doesn't embed them. You must download and add them as `epub.EpubImage` items. Identify image URLs from the article HTML (not web_extract output, which loses them).
- **Use SSL context for image downloads** — Substack CDN URLs may fail certificate verification; create an unverified SSL context.
- **Clean markdown formatting from headings** — headings may contain `**bold**` or `_italic_` markers; strip these for the chapter title.
- **Verify content completeness** — after generating the EPUB, extract all text and compare word count against the original article. Check for key phrases to ensure nothing was lost.
- **Strip Substack noise aggressively** — when converting Substack articles, remove: author avatars (`avatar` in URL), "Discussion about this post", "Leave a comment", "Ready for more?", "Whenever you're ready", "Special thanks to", "Enjoyed the article?", "Restack", "Subscribe", "Images", "If not otherwise stated", "CommentsRestacks", and any subscription/CTA sections. Find the first `# ` heading for article start, and the first discussion/comment marker for article end.
- **ebooklib requires non-empty body content** — every `EpubHtml` item must have non-empty content or `epub.write_epub()` raises `ParserError: Document is empty`. Always provide at least a placeholder `<p>` for chapters without content.
- **No backslashes in f-string expressions** — Python f-strings cannot contain backslashes in the `{}` expression part. Assign the value to a variable first, then use the variable in the f-string.
- **web_extract cache files have line numbers** — when reading cached web_extract output from `AppData/Local/hermes/cache/web/`, lines are prefixed with `LINE_NUM|`. Strip the prefix before parsing.
- **web_extract truncation** — when `web_extract` returns truncated content (head+tail with a footer pointing to a saved file), read the full file from the path in the footer using `read_file()`. The saved file is the complete page content.
- **Substack `<span>` text joining** — Substack HTML often wraps text in `<span>` elements inside `<p>` tags. Using `get_text(strip=True)` joins span text without spaces (e.g., "isfeedback"). Always use `get_text(separator=' ', strip=True)` to preserve word boundaries.
- **User requires actual HTML parsing** — the user explicitly rejects hardcoded or invented chapter headings. Always extract headings from the source: parse `<h2>` tags from HTML, or `##` headings from web_extract markdown. Never manually define section breaks or chapter names.
- **Notion file upload workaround (free plan / Windows)** — `ntn files create` fails on free plans with "does not support multipart uploads". The 3-step HTTP flow (create upload → PUT bytes) also fails with `invalid_request_url` on the PUT step. **Working alternative**: upload the file to external hosting (e.g., `https://tmpfiles.org/api/v1/upload` via `multipart/form-data`), then add it to the page as an external file block:
```json
{"type": "file", "file": {"type": "external", "external": {"url": "https://tmpfiles.org/.../file.epub"}}}
```
This works on all plans and platforms. External file blocks display and download natively in Notion.
- **Telegram bot for EPUB delivery** — For sharing EPUBs to mobile, a Telegram bot is the fastest method. See `scripts/telegram_bot.py` for a template and `references/sharing-methods.md` for setup. The bot accepts URLs, converts to EPUB, and sends the file back — works on mobile without any additional apps.

## Output Location

Save to `F:/Articles/` for web articles (not `F:/Articles/YT/` which is for YouTube transcripts).
