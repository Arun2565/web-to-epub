#!/usr/bin/env python3
"""Convert YouTube transcript to EPUB with raw timestamped lines.

Usage:
    python transcript_to_epub.py transcript.txt output.epub
    python fetch_transcript.py "URL" --text-only --timestamps | python transcript_to_epub.py
"""

import re
import sys
from datetime import datetime
from pathlib import Path
from ebooklib import epub


def parse_transcript(text):
    """Parse transcript into (timestamp, text) pairs."""
    lines = text.strip().split('\n')
    entries = []
    current_ts = None
    current_text = []

    for line in lines:
        m = re.match(r'^(\d{1,2}:\d{2}(?::\d{2})?)\s+(.*)', line)
        if m:
            if current_ts is not None:
                entries.append((current_ts, ' '.join(current_text)))
            current_ts = m.group(1)
            current_text = [m.group(2)]
        else:
            if current_ts is not None:
                current_text.append(line)

    if current_ts is not None:
        entries.append((current_ts, ' '.join(current_text)))

    return entries


def ts_to_seconds(ts):
    parts = ts.split(':')
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0


def ts_to_hms(ts):
    total = ts_to_seconds(ts)
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def chunk_entries(entries, chunk_size=30):
    chunks = []
    for i in range(0, len(entries), chunk_size):
        chunk = entries[i:i+chunk_size]
        chunks.append({
            'start': chunk[0][0],
            'end': chunk[-1][0],
            'entries': chunk
        })
    return chunks


def create_epub(transcript_text, output_path, title="YouTube Transcript", url="", speaker=""):
    entries = parse_transcript(transcript_text)
    chunks = chunk_entries(entries, chunk_size=30)

    book = epub.EpubBook()

    safe_id = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')[:40]
    book.set_identifier(f'yt-raw-{safe_id}')
    book.set_title(title)
    book.set_language('en')
    book.add_author(speaker or 'YouTube Transcript')
    book.add_metadata('DC', 'publisher', 'Hermes Agent')
    book.add_metadata('DC', 'description', f'Transcript of: {url}' if url else 'YouTube video transcript')
    book.add_metadata('DC', 'date', datetime.now().strftime('%Y-%m-%d'))

    style = '''
    body { font-family: 'Georgia', 'Times New Roman', serif; line-height: 1.6; margin: 2em; color: #1a1a1a; }
    h1 { font-size: 1.8em; margin-bottom: 0.3em; border-bottom: 2px solid #c0392b; padding-bottom: 0.3em; }
    h2 { font-size: 1.3em; margin-top: 2em; color: #2c3e50; }
    .timestamp { color: #c0392b; font-family: 'Courier New', monospace; font-weight: bold; margin-right: 0.5em; }
    .line { margin-bottom: 0.8em; text-align: justify; }
    .url { color: #2980b9; font-size: 0.9em; }
    .meta { color: #7f8c8d; font-size: 0.85em; margin-bottom: 2em; }
    '''
    nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=style)
    book.add_item(nav_css)

    title_page = epub.EpubHtml(title='Title Page', file_name='title_page.xhtml')
    title_page.content = f'''
    <html><head><title>{title}</title></head>
    <body>
        <h1>{title}</h1>
        {f'<p class="meta">Speaker: {speaker}</p>' if speaker else ''}
        {f'<p class="meta">Source: <a class="url" href="{url}">{url}</a></p>' if url else ''}
        <p class="meta">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
        <p class="meta">Total lines: {len(entries)}</p>
    </body></html>
    '''
    book.add_item(title_page)

    chapters = []
    for i, chunk in enumerate(chunks):
        chapter = epub.EpubHtml(
            title=f"Lines {i*30+1}-{min((i+1)*30, len(entries))}",
            file_name=f'chapter_{i+1:03d}.xhtml'
        )

        lines_html = []
        for ts, text in chunk['entries']:
            ts_hms = ts_to_hms(ts)
            lines_html.append(f'<p class="line"><span class="timestamp">[{ts_hms}]</span>{text}</p>')

        chapter.content = f'''
        <html><head><title>Lines {i*30+1}-{min((i+1)*30, len(entries))}</title></head>
        <body>
            <h2>Lines {i*30+1}–{min((i+1)*30, len(entries))}</h2>
            {''.join(lines_html)}
        </body></html>
        '''
        book.add_item(chapter)
        chapters.append(chapter)

    book.toc = [title_page] + chapters
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ['nav', title_page] + chapters

    epub.write_epub(output_path, book)
    return len(entries), len(chunks)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Convert YouTube transcript to EPUB (raw format)')
    parser.add_argument('input', nargs='?', help='Input file (default: stdin)')
    parser.add_argument('output', nargs='?', help='Output EPUB path (default: transcript.epub)')
    parser.add_argument('--title', default='YouTube Transcript')
    parser.add_argument('--url', default='')
    parser.add_argument('--speaker', default='')
    args = parser.parse_args()

    if args.input:
        text = Path(args.input).read_text(encoding='utf-8')
    else:
        text = sys.stdin.read()

    output = args.output or 'transcript.epub'
    total_lines, total_chunks = create_epub(text, output, args.title, args.url, args.speaker)
    print(f"EPUB created: {output}")
    print(f"Total transcript lines: {total_lines}")
    print(f"Total chapters: {total_chunks}")


if __name__ == '__main__':
    main()
