#!/usr/bin/env python3
"""YouTube helper — fetch chapters and assign them to transcript turns."""

import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import yt_dlp


def get_youtube_chapters(url):
    """Extract video chapters from YouTube URL using yt-dlp.
    
    Returns: {'title': str, 'chapters': [(start_seconds, title), ...]}, error_string
    """
    parsed = urlparse(url)
    if parsed.hostname == 'youtu.be':
        vid = parsed.path.strip('/').split('?')[0]
    else:
        m = re.search(r'v=([a-zA-Z0-9_-]{11})', parsed.query)
        vid = m.group(1) if m else None
    if not vid:
        return None, "Could not extract video ID"
    
    ydl_opts = {'quiet': True, 'no_warnings': True, 'skip_download': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f'https://www.youtube.com/watch?v={vid}', download=False)
            if not info:
                return None, "Could not extract video info"
            chapters = [(c.get('start_time', 0), c.get('title', '')) for c in info.get('chapters', [])]
            return {'title': info.get('title', ''), 'chapters': chapters}, None
    except Exception as e:
        return None, f"yt-dlp error: {str(e)}"


def get_youtube_transcript(url):
    """Fetch YouTube transcript using youtube-transcript-api."""
    parsed = urlparse(url)
    if parsed.hostname == 'youtu.be':
        vid = parsed.path.strip('/').split('?')[0]
    else:
        m = re.search(r'v=([a-zA-Z0-9_-]{11})', parsed.query)
        vid = m.group(1) if m else None
    if not vid:
        return None, "Could not extract video ID"
    
    skill_dir = Path(r"C:/Users/rohit/AppData/Local/hermes/skills/media/youtube-content")
    result = subprocess.run(
        [sys.executable, str(skill_dir / "scripts/fetch_transcript.py"),
         f"https://www.youtube.com/watch?v={vid}", "--text-only", "--timestamps"],
        capture_output=True, text=True, timeout=60, cwd=str(skill_dir)
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None, f"Could not fetch transcript: {result.stderr or 'unknown error'}"
    return result.stdout, None


def timestamp_to_seconds(ts):
    """Convert HH:MM:SS or MM:SS to seconds."""
    parts = ts.split(':')
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0


def assign_chapters_to_turns(turns, chapters):
    """Assign chapter names to speaker turns based on timestamps.
    
    turns: list of {'speaker': str, 'start': str, 'text': str}
    chapters: list of (start_seconds, title)
    
    Returns: list of {'chapter': str, 'turns': [turn, ...]}
    """
    if not chapters:
        return [{'chapter': 'Full Video', 'turns': turns}]
    
    chapters_with_end = []
    for i, (start, title) in enumerate(chapters):
        end = chapters[i+1][0] if i+1 < len(chapters) else float('inf')
        chapters_with_end.append((start, end, title))
    
    grouped = []
    current_chapter = chapters_with_end[0][2]
    current_turns = []
    
    for turn in turns:
        turn_start = timestamp_to_seconds(turn['start'])
        for start, end, title in chapters_with_end:
            if start <= turn_start < end:
                if title != current_chapter:
                    if current_turns:
                        grouped.append({'chapter': current_chapter, 'turns': current_turns})
                    current_chapter = title
                    current_turns = []
                break
        current_turns.append(turn)
    
    if current_turns:
        grouped.append({'chapter': current_chapter, 'turns': current_turns})
    
    return grouped


if __name__ == '__main__':
    url = sys.argv[1] if len(sys.argv) > 1 else "https://youtu.be/UWjh5Z4s8jY"
    info, err = get_youtube_chapters(url)
    if err:
        print(f"Error: {err}")
    else:
        print(f"Title: {info['title']}")
        print(f"Chapters: {len(info['chapters'])}")
        for start, title in info['chapters']:
            print(f"  {start:>6.0f}s  {title}")
