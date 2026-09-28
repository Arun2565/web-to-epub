# epub-landing Server Reference

Server: `F:/epub-landing/server.py` (Flask, port 8765)

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/make-epub` | Convert single YT URL → EPUB |
| POST | `/api/make-playlist-epub` | Convert YT playlist → multi-part EPUB |
| GET | `/output/<filename>` | Serve generated EPUB |
| GET | `/api/download/<filename>` | Download generated EPUB |

## Pipeline

1. Frontend (`index.html`) POSTs URL to `/api/make-epub`
2. Server fetches chapters via yt-dlp
3. Fetches transcript via youtube-transcript-api
4. Generates EPUB with named chapters
5. Returns filename; frontend opens `reader.html?book=<filename>`

## VTT Deduplication Pattern

Auto-generated subtitles repeat phrases. The `vtt_to_text` function in `playlist_to_epub.py`:

```python
def vtt_to_text(vtt):
    lines = vtt.strip().split('\n')
    output = []
    current_start = None
    current_text = []
    seen_text = set()

    for line in lines:
        line = line.strip()
        if not line or line == 'WEBVTT' or line.startswith('NOTE'):
            continue

        ts_match = re.match(r'(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->', line)
        if ts_match:
            if current_start and current_text:
                text = ' '.join(current_text)
                text = re.sub(r'<[^>]+>', '', text)  # clean VTT tags
                text = re.sub(r'\s+', ' ', text).strip()
                words = text.split()
                if len(words) > 3:
                    deduped = [w for i, w in enumerate(words) if i < 3 or w != words[i-3]]
                    text = ' '.join(deduped)
                if text.strip() and text[:50] not in seen_text:
                    output.append(f"{current_start} {text.strip()}")
                    seen_text.add(text[:50])
            # reset for next segment
            ...
```

Key dedup: sliding window of 3 words to catch repeated phrases (common in auto-captions).
