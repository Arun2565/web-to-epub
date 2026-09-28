#!/usr/bin/env python3
"""Convert YouTube transcript (with timestamps) to EPUB with natural Q&A formatting.

Usage:
    python transcript_to_epub_conversation.py transcript.txt output.epub
    python fetch_transcript.py "URL" --text-only --timestamps | python transcript_to_epub_conversation.py
"""

import re
import sys
from datetime import datetime
from pathlib import Path
from ebooklib import epub


def parse_transcript(text):
    """Parse transcript into (timestamp, speaker_marker, text) tuples."""
    lines = text.strip().split('\n')
    entries = []
    current_ts = None
    current_speaker = None
    current_text = []

    for line in lines:
        m = re.match(r'^(\d{1,2}:\d{2}(?::\d{2})?)\s+(.*)', line)
        if m:
            if current_ts is not None:
                entries.append((current_ts, current_speaker, ' '.join(current_text)))
            
            current_ts = m.group(1)
            rest = m.group(2)
            
            speaker_match = re.match(r'^>>\s*(.*)', rest)
            if speaker_match:
                current_speaker = '>>'
                current_text = [speaker_match.group(1).strip()]
            else:
                current_speaker = None
                current_text = [rest]
        else:
            if current_ts is not None:
                current_text.append(line)

    if current_ts is not None:
        entries.append((current_ts, current_speaker, ' '.join(current_text)))

    return entries


def identify_speakers(entries):
    """Identify who is speaking based on '>>' markers.
    
    Lines before first '>>' → guest (intro/outro).
    After first '>>', speakers alternate: host, guest, host, guest...
    """
    result = []
    current_speaker = 'karan'
    first_marker_seen = False
    marker_count = 0
    
    for ts, marker, text in entries:
        if marker == '>>':
            if not first_marker_seen:
                first_marker_seen = True
                current_speaker = 'peter'
                marker_count = 1
            else:
                marker_count += 1
                if marker_count % 2 == 1:
                    current_speaker = 'peter'
                else:
                    current_speaker = 'karan'
            result.append((ts, current_speaker, text))
        else:
            if not first_marker_seen:
                result.append((ts, 'karan', text))
            else:
                result.append((ts, current_speaker, text))
    
    return result


def group_into_turns(entries):
    """Group consecutive lines by same speaker into turns."""
    if not entries:
        return []
    
    turns = []
    current_speaker = entries[0][1]
    current_start = entries[0][0]
    current_text = [entries[0][2]]
    
    for ts, speaker, text in entries[1:]:
        if speaker == current_speaker:
            current_text.append(text)
        else:
            turns.append({
                'speaker': current_speaker,
                'start': current_start,
                'text': ' '.join(current_text)
            })
            current_speaker = speaker
            current_start = ts
            current_text = [text]
    
    turns.append({
        'speaker': current_speaker,
        'start': current_start,
        'text': ' '.join(current_text)
    })
    
    return turns


def group_into_exchanges(turns, max_per_chapter=10):
    """Group turns into Q&A exchanges and split into chapters."""
    chapters = []
    current_chapter = []
    exchange_count = 0
    
    for turn in turns:
        current_chapter.append(turn)
        if turn['speaker'] == 'karan':
            exchange_count += 1
        
        if exchange_count >= max_per_chapter:
            chapters.append(current_chapter)
            current_chapter = []
            exchange_count = 0
    
    if current_chapter:
        chapters.append(current_chapter)
    
    return chapters


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


def clean_text(text):
    """Remove stage directions like [music], [laughter], etc."""
    text = re.sub(r'\[(?:music|laughter|clears throat|snorts)\]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def create_epub(transcript_text, output_path, title="YouTube Transcript", url="", speaker=""):
    entries = parse_transcript(text=transcript_text)
    speakers = identify_speakers(entries)
    turns = group_into_turns(speakers)
    chapters = group_into_exchanges(turns, max_per_chapter=10)

    book = epub.EpubBook()

    safe_id = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')[:40]
    book.set_identifier(f'yt-conv-{safe_id}')
    book.set_title(title)
    book.set_language('en')
    book.add_author(speaker or 'YouTube Transcript')
    book.add_metadata('DC', 'publisher', 'Hermes Agent')
    book.add_metadata('DC', 'description', f'Transcript of: {url}' if url else 'YouTube video transcript')
    book.add_metadata('DC', 'date', datetime.now().strftime('%Y-%m-%d'))

    style = '''
    body { 
        font-family: 'Georgia', 'Times New Roman', serif; 
        line-height: 1.7; 
        margin: 2em; 
        color: #1a1a1a; 
        max-width: 40em;
        margin-left: auto;
        margin-right: auto;
    }
    h1 { 
        font-size: 1.8em; 
        margin-bottom: 0.3em; 
        border-bottom: 2px solid #c0392b; 
        padding-bottom: 0.3em; 
        text-align: center;
    }
    h2 { 
        font-size: 1.2em; 
        margin-top: 2.5em; 
        margin-bottom: 1em;
        color: #2c3e50;
        border-bottom: 1px solid #bdc3c7;
        padding-bottom: 0.3em;
    }
    .meta { 
        color: #7f8c8d; 
        font-size: 0.9em; 
        margin-bottom: 2em; 
        text-align: center;
    }
    .exchange {
        margin-bottom: 1.8em;
    }
    .question {
        margin-bottom: 0.8em;
        padding-left: 1em;
        border-left: 3px solid #3498db;
    }
    .answer {
        margin-bottom: 0.8em;
        padding-left: 1em;
        border-left: 3px solid #e67e22;
    }
    .speaker {
        font-weight: bold;
        font-size: 0.85em;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.2em;
    }
    .peter .speaker { color: #2980b9; }
    .karan .speaker { color: #d35400; }
    .timestamp {
        color: #95a5a6;
        font-size: 0.75em;
        font-family: 'Courier New', monospace;
        margin-left: 0.5em;
    }
    .text {
        text-align: justify;
    }
    .url { color: #2980b9; font-size: 0.9em; }
    .chapter-meta {
        color: #7f8c8d;
        font-size: 0.8em;
        margin-bottom: 1.5em;
        font-style: italic;
    }
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
        <p class="meta">Total exchanges: {sum(1 for t in turns if t['speaker'] == 'karan')}</p>
    </body></html>
    '''
    book.add_item(title_page)

    chapter_objs = []
    for i, chapter_turns in enumerate(chapters):
        chapter = epub.EpubHtml(
            title=f"Chapter {i+1}",
            file_name=f'chapter_{i+1:03d}.xhtml'
        )

        first_ts = chapter_turns[0]['start']
        last_ts = chapter_turns[-1]['start']

        exchanges_html = []
        for turn in chapter_turns:
            speaker_class = turn['speaker']
            speaker_name = 'Peter' if turn['speaker'] == 'peter' else 'Karan'
            ts_hms = ts_to_hms(turn['start'])
            cleaned = clean_text(turn['text'])
            
            exchanges_html.append(f'''
            <div class="exchange {speaker_class}">
                <div class="speaker">{speaker_name} <span class="timestamp">[{ts_hms}]</span></div>
                <div class="text">{cleaned}</div>
            </div>
            ''')

        chapter.content = f'''
        <html><head><title>Chapter {i+1}</title></head>
        <body>
            <h2>Chapter {i+1}</h2>
            <p class="chapter-meta">From {ts_to_hms(first_ts)} to {ts_to_hms(last_ts)}</p>
            {''.join(exchanges_html)}
        </body></html>
        '''
        book.add_item(chapter)
        chapter_objs.append(chapter)

    book.toc = [title_page] + chapter_objs
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ['nav', title_page] + chapter_objs

    epub.write_epub(output_path, book)
    return len(turns), len(chapters)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Convert YouTube transcript to EPUB with Q&A formatting')
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
    total_turns, total_chapters = create_epub(text, output, args.title, args.url, args.speaker)
    print(f"EPUB created: {output}")
    print(f"Total speaker turns: {total_turns}")
    print(f"Total chapters: {total_chapters}")


if __name__ == '__main__':
    main()
