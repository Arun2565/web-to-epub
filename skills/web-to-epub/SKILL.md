---
name: web-to-epub
description: "Convert YouTube videos, Substack podcasts, and web articles into structured EPUB ebooks for offline reading. Detects monologue vs conversation format, generates named chapters from content analysis, embeds images, and supports both transcript styles. Handles YouTube URLs, Substack posts, and general web articles."
version: 2.0.0
author: Rohit, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [youtube, epub, transcript, video, conversion, substack, web]
    related_skills: [website-to-epub]
---

# YouTube/Web to EPUB

Convert YouTube video transcripts, Substack posts, and web articles into EPUB ebook files for offline reading.

## When to use

- User provides a YouTube URL and wants an ebook
- User wants a video transcript formatted as a readable document
- User wants interview/podcasts transcripts as structured Q&A
- User provides a Substack URL with a transcript
- User wants a narrated video transcript as clean paragraph-style text
- User provides a web article URL to convert to EPUB

Don't use for:
- Simple single-page articles without transcripts (use website-to-epub)
- Videos with disabled transcripts
- Private/unavailable videos

## Prerequisites

```bash
pip install youtube-transcript-api ebooklib yt-dlp
```

On Windows with MSYS/bash: use `python` directly (uv may need venv setup).

## Workflow

### 1. Identify Source Type

Detect whether the input is a YouTube URL, Substack URL, or general web page:

```python
from urllib.parse import urlparse

def detect_source_type(url):
    parsed = urlparse(url)
    if parsed.hostname in ('youtu.be', 'www.youtube.com', 'youtube.com'):
        return 'youtube'
    elif 'substack.com' in parsed.hostname:
        return 'substack'
    else:
        return 'web'
```

### 2. Fetch Content

#### YouTube Transcript

```python
from youtube_transcript_api import YouTubeTranscriptApi

def fetch_youtube_transcript(video_id):
    """Fetch transcript using youtube-transcript-api."""
    api = YouTubeTranscriptApi()
    transcript = api.fetch(video_id)
    entries = []
    for entry in transcript:
        entries.append({
            'start': entry.start,
            'text': entry.text
        })
    return entries
```

**API note**: In newer versions of `youtube-transcript-api`, `fetch()` is an instance method: `YouTubeTranscriptApi().fetch(video_id)`. The class method `YouTubeTranscriptApi.get_transcript(video_id)` was removed.

#### YouTube Metadata (yt-dlp)

```python
import yt_dlp

def fetch_youtube_metadata(url):
    """Fetch video metadata including chapters."""
    ydl_opts = {'quiet': True, 'no_warnings': True, 'skip_download': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            'title': info.get('title', ''),
            'duration': info.get('duration', 0),
            'chapters': info.get('chapters', []),
            'description': info.get('description', '')
        }
```

Chapters are critical — user wants named chapters (e.g. "How Hermes differs from Claude Code"), not generic "Lines 1-10".

#### Substack/Web Transcript

For Substack posts with transcripts (Dwarkesh Podcast format):
- URL contains `substack.com/home/post/`
- Parse `<article>` content, find "Transcript" marker
- Split by `<h3>` tags with timestamp pattern `HH:MM:SS - Title`
- Parse `<p><strong>Speaker</strong>: text</p>` for speaker turns
- Group by chapter sections

Use `web_extract` tool to get the page content, then parse the HTML.

#### General Web Articles

For general web articles, use `web_extract` tool as the primary method — it returns clean markdown/text that can be parsed directly. Fall back to `requests` + `BeautifulSoup` only if `web_extract` fails (paywall, bot wall, etc.).

```python
# Preferred: use web_extract tool (returns markdown)
# Then parse headings with regex: re.match(r'^#{1,3}\s+(.+)', line)

# Fallback: requests + BeautifulSoup
from bs4 import BeautifulSoup
import requests

url = "https://example.com/article"
html = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).text
soup = BeautifulSoup(html, 'html.parser')
article = soup.find('article')
main = soup.find('main')
content = article or main or soup.find(class_='content') or soup.find('body')
```

See `references/web-article-format.md` for the full workflow including image download and chapter extraction.

### 3. Detect Format Type

Analyze the transcript to determine formatting:

```python
def detect_format_type(entries):
    """Detect if video is monologue or conversation."""
    total_lines = len(entries)
    quote_lines = sum(1 for e in entries if e['text'].startswith('>>'))
    
    # If >> lines < 10% of total: use monologue format
    # If >> lines >= 10% of total: use conversation format
    if quote_lines < total_lines * 0.1:
        return 'monologue'
    return 'conversation'
```

### 4. Generate EPUB

#### Monologue Format (for narrated videos, explainers, essays)

For videos with few or no `>>` markers:

- **Group consecutive lines into paragraphs** based on timing gaps (>2 seconds between lines = new paragraph)
- **No per-line timestamps** — only chapter-level time ranges (e.g., "From 00:00 to 01:58")
- **Speaker label once per paragraph** — "Ksenia" or "Researcher" as a heading, not inline
- **Clean justified text** — paragraphs flow naturally like a transcript, not a subtitle file
- **Quote styling** — `>>` lines get blue left border, light background, italicized
- **Named chapters** — analyze content for topic keywords, generate meaningful titles (not "Chapter 1")
- **Chapter breaks** — every ~2 minutes of video time
- **No repeated speaker labels** — for single-speaker videos, narrator paragraphs have no speaker label; only quotes get labeled

#### Conversation Format (for interviews/podcasts)

For videos with two speakers in dialogue:

- Parses `>>` speaker markers to identify who is talking
- Groups consecutive lines by same speaker into turns
- Alternates between speakers (Peter/Karan, Host/Guest, etc.)
- Cleans stage directions: `[music]`, `[laughter]`, `[clears throat]`, `[snorts]`
- Groups turns into chapters (~10 exchanges each)
- Produces clean typography with speaker names, timestamps, and justified text

Speaker identification logic:
- Lines before first `>>` marker → guest (intro/outro)
- First `>>` → host/interviewer
- Subsequent `>>` lines alternate between host and guest
- Non-marker lines inherit the last identified speaker

#### Web Article Format

For general web articles:

| HTML Element | EPUB Mapping |
|-------------|--------------|
| `<h1>` | Chapter title |
| `<h2>` | Section heading |
| `<h3>` | Subsection heading |
| `<p>` | Body paragraph |
| `<ul>` / `<ol>` | List |
| `<pre>` | Code block |
| `<figure>` | Figure with caption |
| `<blockquote>` | Blockquote |
| `<table>` | Table |

Skip: nav, footer, header, aside, comments, share bars, related posts, site TOCs.

## Output Format — Monologue Style Example

```html
<h2>Introduction: What is a World Model?</h2>
<p class="meta">From 00:00 to 01:56</p>

<div class="narrator">
    <p>So we used to talk about it as building a world model. Workshop at Chicago Booth...</p>
</div>

<div class="quote">
    <p class="speaker">Researcher</p>
    <p>We all have world models in our head...</p>
</div>

<div class="narrator">
    <p>Researchers are saying they're building world models...</p>
</div>
```

Key: No "Ksenia" label on narrator paragraphs — only quotes get speaker labels.

## Output Format — Conversation Style Example

```html
<h2>Chapter 1</h2>
<p class="chapter-meta">From 00:00 to 20:56</p>

<div class="exchange karan">
    <div class="speaker">Karan <span class="timestamp">[00:00]</span></div>
    <div class="text">In 2012, Linus Torvalds called Nvidia...</div>
</div>

<div class="exchange peter">
    <div class="speaker">Peter <span class="timestamp">[00:12]</span></div>
    <div class="text">And Nvidia has been the single worst company...</div>
</div>
```

## Output Format — Web Article Example

```html
<h2>Article Title</h2>
<p>First paragraph of the article...</p>
<p>Second paragraph...</p>

<h2>Section Heading</h2>
<p>Content under this section...</p>
```

## Images in EPUB

**Always include images from the original article in the EPUB.** This is critical for a good reading experience.

### How to add images

1. **Extract image URLs** from the web page content (look for `substackcdn.com/image/fetch/...` or similar CDN URLs)
2. **Download images** locally using `urllib.request` with a `User-Agent` header
3. **Detect actual format** — don't trust the URL extension. Substack CDNs often return PNG data for `.svg` URLs. Check the file header bytes:
   - `\x89PNG` = PNG
   - `\xff\xd8\xff` = JPEG
   - `<svg` = actual SVG
4. **Add to EPUB** as `epub.EpubItem` with correct `media_type`:
   - `image/png` for PNG files
   - `image/jpeg` for JPEG files
   - `image/svg+xml` for actual SVG files
5. **Reference in HTML** with `<img src="images/filename.png" alt="description"/>`
6. **Wrap in container** for styling: `<div class="image-container">...</div>`

### Common pitfall

Substack CDN URLs ending in `.svg` often return PNG data. If the manifest says `image/svg` but the bytes are PNG, EPUB readers (Apple Books, Calibri, Kindle) will silently skip the image. Always verify the actual file format from the header bytes, not the URL extension.

### CSS for images

```css
img { max-width: 100%; height: auto; display: block; margin: 1em auto; border-radius: 4px; }
.image-container { text-align: center; margin: 1.5em 0; }
.image-caption { font-size: 0.85em; color: #666; font-style: italic; margin-top: 0.3em; }
```

## CSS Styling

```css
body { 
    font-family: Georgia, serif; 
    line-height: 1.6; 
    margin: 5%; 
    color: #1a1a1a; 
}
h1 { 
    font-size: 1.5em; 
    margin-bottom: 0.5em; 
}
h2 { 
    font-size: 1.3em; 
    margin-top: 1.5em; 
    margin-bottom: 0.5em; 
    border-bottom: 1px solid #ccc; 
    padding-bottom: 0.3em; 
}
p { 
    margin: 0.8em 0; 
    text-align: justify; 
}
p.speaker { 
    margin-top: 1.5em; 
    margin-bottom: 0.3em; 
    color: #333; 
    font-weight: bold; 
    font-size: 0.9em; 
    text-transform: uppercase; 
}
.quote {
    margin: 1em 0;
    padding-left: 1.5em;
    border-left: 3px solid #3498db;
    background-color: #f8f9fa;
    padding: 0.8em 1em 0.8em 1.5em;
    border-radius: 0 4px 4px 0;
    font-style: italic;
}
.narrator {
    margin: 1em 0;
}
a { 
    color: #0066cc; 
    text-decoration: none; 
}
.meta { 
    color: #7f8c8d; 
    font-size: 0.9em; 
    margin-bottom: 2em; 
}
.url { 
    color: #2980b9; 
    font-size: 0.9em; 
}
```

## Dependencies

- `youtube-transcript-api` — fetches YT transcripts
- `ebooklib` — generates EPUB files
- `yt-dlp` — fetches video metadata and chapters
- `beautifulsoup4` — parses HTML for web articles
- `requests` — fetches web pages

## Error Handling

- **Transcript disabled**: tell user; suggest checking subtitles on video page
- **Private/unavailable**: relay error, ask user to verify URL
- **No matching language**: retry without `--language` to get any available transcript
- **Connection errors**: retry (transient network issues are common)
- **MSYS path issues**: use absolute paths like `C:/Users/...` instead of `/tmp/...`
- **Chapter metadata missing**: if yt-dlp fails, fall back to grouping by speaker turns without chapter names
- **Video download blocked**: YouTube often blocks video downloads with 403. Use thumbnails instead of video frames.
- **youtube-transcript-api version mismatch**: Use `YouTubeTranscriptApi().fetch(video_id)` (instance method). The class method `YouTubeTranscriptApi.get_transcript(video_id)` was removed in newer versions.

## Windows/MSYS Quirks

- `/tmp/` doesn't exist — use `C:/Users/rohit/` or `$TEMP`
- `uv` may fail — fall back to `python` directly
- `python3` may not be aliased — use `python` (check with `python --version`)
- Paths with backslashes in Python strings: use raw strings `r"C:\..."` or forward slashes `"C:/..."` to avoid escape sequence errors (`\U` in paths causes SyntaxWarning)
- `yt-dlp` is installed as `yt_dlp` Python module — import as `import yt_dlp`

## epub-landing Server Integration

The user runs a Flask server at `F:/epub-landing/server.py` that provides a URL→EPUB pipeline:

- `POST /api/make-epub` — fetches a YouTube URL, generates an EPUB, returns the filename
- `POST /api/make-playlist-epub` — processes entire playlists
- `GET /output/<filename>` — serves generated EPUBs
- Frontend at `index.html` pastes URLs; `reader.html` opens generated books

When working on epub-landing, the server must be running (`python server.py 8765`) for the frontend to work. The server uses `yt-dlp` for chapter metadata and `youtube-transcript-api` for transcripts.

## VTT Deduplication

YouTube auto-generated transcripts often repeat phrases. The `vtt_to_text` function in `playlist_to_epub.py` includes deduplication logic:
- Tracks seen text prefixes to avoid duplicate entries
- Removes repeated word sequences (sliding window of 3 words)
- Cleans VTT tags (`<c>`, `</c>`) and HTML entities

This is critical for auto-generated subtitles where the API returns overlapping segments.

## Substack Podcast Converter

For Substack posts with transcripts (Dwarkesh Podcast format):
- URL contains `substack.com/home/post/`
- Parse `<article>` content, find "Transcript" marker
- Split by `<h3>` tags with timestamp pattern `HH:MM:SS - Title`
- Parse `<p><strong>Speaker</strong>: text</p>` for speaker turns
- Group by chapter sections

## Chapter Naming

Generate meaningful chapter titles based on content analysis:

```python
def generate_chapter_titles(chapters):
    """Generate meaningful chapter titles based on content analysis."""
    titles = []
    used_titles = set()
    
    # Define topic patterns with keywords
    topic_patterns = [
        (['driving', 'changing lanes', 'mirror', 'car'], "The Driving Analogy"),
        (['latent', 'representation', 'compressed', 'state'], "Latent States and Compression"),
        (['pixel', 'video', 'sora', 'kling', 'frame'], "Predicting Pixels: Video World Models"),
        (['muzero', 'board', 'screen', 'action', 'reward'], "MuZero: Learning from Actions"),
        (['prediction', 'error', 'model predictive control'], "Model Predictive Control"),
        (['color', 'visual', 'appearance', 'pushing', 'block'], "The Color Change Problem"),
        (['physic', 'gymnast', 'backflip', 'momentum', 'conservation'], "Physical Consistency vs Visual Realism"),
        (['agi', 'path', 'test', 'intervene', 'cause', 'effect'], "Are World Models the Path to AGI?"),
        (['world model', 'building', 'same thing', 'two videos'], "Introduction: What is a World Model?"),
    ]
    
    for i, chapter_paras in enumerate(chapters):
        narrator_texts = [p['text'] for p in chapter_paras if p['speaker'] == 'narrator']
        quote_texts = [p['text'] for p in chapter_paras if p['speaker'] == 'quote']
        
        if not narrator_texts:
            titles.append(f"Chapter {i + 1}")
            continue
        
        all_text = ' '.join(narrator_texts).lower() + ' ' + ' '.join(quote_texts).lower()
        
        # Find best matching topic
        best_score = 0
        best_title = None
        for keywords, title in topic_patterns:
            score = sum(1 for kw in keywords if kw in all_text)
            if score > best_score:
                best_score = score
                best_title = title
        
        # Handle duplicates
        if best_title and best_title in used_titles:
            for keywords, title in topic_patterns:
                if title == best_title:
                    continue
                score = sum(1 for kw in keywords if kw in all_text)
                if score >= 2 and title not in used_titles:
                    best_title = title
                    break
        
        if best_title and best_score >= 2:
            titles.append(best_title)
            used_titles.add(best_title)
        else:
            # Fallback: use first sentence
            first_text = narrator_texts[0]
            first_sentence = first_text.split('.')[0].split('?')[0].split('!')[0]
            if len(first_sentence) > 60:
                first_sentence = first_sentence[:57] + '...'
            first_sentence = first_sentence.replace('So ', '').replace('Um, ', '')
            
            base_title = first_sentence
            counter = 1
            while first_sentence in used_titles:
                counter += 1
                first_sentence = f"{base_title} ({counter})"
            titles.append(first_sentence)
            used_titles.add(first_sentence)
    
    return titles
```

## Support Files

- `scripts/yt_helper.py` — fetch YT chapters via yt-dlp + assign chapters to turns
- `scripts/telegram_bot.py` — Telegram bot for URL→EPUB conversion (see Sharing Methods)
- `references/epub-format-notes.md` — EPUB structure and styling reference
- `references/epub-landing-server.md` — epub-landing Flask server endpoints & VTT dedup reference
- `references/named-chapters.md` — how to use video chapters for EPUB structure
- `references/substack-transcript-parsing.md` — Substack transcript parsing guide
- `references/substack-epub-cleanup.md` — Substack EPUB cleanup & repair (for pre-existing Substack EPUBs)
- `references/monologue-format.md` — monologue paragraph transcription format and chapter naming
- `references/web-article-format.md` — web article extraction and formatting guide
- `references/sharing-methods.md` — sharing EPUBs to mobile (Telegram bot, local server, cloud)

### 5. HuggingFace Blog Cleanup

HuggingFace blog posts (`huggingface.co/blog/`) inject platform-specific chrome that must be stripped:

- **Avatar images**: Lines matching `- [![](url)](link "author")` — remove
- **Upvote buttons**: Multi-line `[Upvote \\n\\n count](link)` blocks — remove
- **Follow buttons**: `[Name\\nusername\\n\\nFollow](link)` — remove
- **Back to Articles**: Top-of-page link — remove
- **More Articles from our Blog** / **More from this author**: Remove the section and everything after
- **Spaces mentioned in this article**: Remove the section and everything after
- **Community section**: Remove `### Community` and everything after
- **Comment UI elements**: `EditPreview`, `Upload images, audio, and videos...`, `Tap or paste here to upload images`, `Comment`

**Key rule**: Find the first `# ` heading (article title) and first `## ` heading (first section) to bound the content. Stop at the first cross-promotional or comment marker.

See `references/web-article-format.md` for the full web article workflow.

1. **Substack heading cleanup is the hardest part** — Substack injects `<div class="pencraft...">` elements INSIDE heading tags: `<h2>Title<div...>...</div></h2>`. A naive regex `<div[^>]*>.*?</div>` will match the wrong closing div (the first nested one, not the one that closes the heading). Use the positional approach: find the first `<div` after the opening tag, take everything before it as the title, reconstruct as `<h2>title</h2>`. See `references/substack-epub-cleanup.md` for the full procedure.

2. **Code blocks must be protected first** — Substack wraps code in `<div class="...code-..." data-line-numbers="true"><pre><code>...</code></pre></div>`. Extract `<pre>` blocks and replace with placeholders BEFORE running any other cleanup regexes, or the code content gets mangled.

3. **Duplicate H1s** — Substack EPUBs sometimes contain both a clean `<h1>Title</h1>` and a crufted `<h1 >Title<div...>...</div></h1>`. Remove ALL H1s from the body and add your own in the chapter template.

4. **Image paths** — Substack EPUBs store images as `img_ch1_xxxx.jpg` at the EPUB root. When rebuilding, copy them to an `images/` directory and fix paths: `html.replace('src="img_', 'src="images/img_')`.

5. **data-attrs on images** — Substack adds `data-attrs="{...JSON...}"` to images. These blobs can break e-readers. Remove them: `re.sub(r'\s+data-attrs="[^"]*"', '', html)`.

6. **Substack article content extraction** — When converting Substack articles, strip ALL promotional content (subscribe buttons, restacks, course ads, sponsor banners, comment sections). See `references/substack-content-extraction.md` for the complete marker list and extraction algorithm. Key rule: scan forward from the first article heading, stop at the FIRST promotional marker, and use a state machine to skip multi-line promotional blocks.