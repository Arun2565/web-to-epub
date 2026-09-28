# Named Chapters

User preference: use video metadata chapter names, never generic "Lines 1-10".

## YouTube

Use `yt-dlp` to extract chapters:

```python
import yt_dlp
with yt_dlp.YoutubeDL({'quiet': True, 'skip_download': True}) as ydl:
    info = ydl.extract_info(url, download=False)
    chapters = [(c['start_time'], c['title']) for c in info.get('chapters', [])]
```

Then assign each speaker turn to a chapter based on its timestamp.

## Substack / Podcasts

Parse `<h3>` or `<h2>` tags with timestamp pattern:

```python
# Substack format: <h3>00:00:00 - Section Title</h3>
# Also: ### 00:00:00 - Section Title  (in markdown)
```

Each section header becomes a chapter.

## Fallback

If no chapters available, group by speaker turns (~10 exchanges/chapter) with generic names like "Part 1", "Part 2".
