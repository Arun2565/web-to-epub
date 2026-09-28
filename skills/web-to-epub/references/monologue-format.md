# Monologue Format — Paragraph Transcription

For narrated videos (monologues, explainers, essays) with few or no `>>` speaker markers.

## When to use

- `>>` lines < 10% of total transcript lines
- Single narrator with occasional quoted excerpts
- Educational/explainer content, video essays, tutorials

## Implementation

### 1. Parse transcript

```python
def parse_transcript(text):
    lines = text.strip().split('\n')
    entries = []
    current_ts = None
    current_speaker = None
    current_text = []

    for line in lines:
        m = re.match(r'^\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?\s+(.*)', line)
        if m:
            if current_ts is not None:
                entries.append((current_ts, current_speaker, ' '.join(current_text)))
            current_ts = m.group(1)
            rest = m.group(2)
            quote_match = re.match(r'^>>\s*(.*)', rest)
            if quote_match:
                current_speaker = 'quote'
                current_text = [quote_match.group(1).strip()]
            else:
                current_speaker = 'narrator'
                current_text = [rest]
        else:
            if current_ts is not None:
                current_text.append(line)

    if current_ts is not None:
        entries.append((current_ts, current_speaker, ' '.join(current_text)))
    return entries
```

### 2. Group into paragraphs

Group consecutive lines by same speaker. Break paragraph when:
- Speaker changes (narrator → quote or vice versa)
- Timing gap > 2 seconds between lines

```python
def group_into_paragraphs(entries, gap_threshold=2):
    paragraphs = []
    current_speaker = entries[0][1]
    current_start = entries[0][0]
    current_text = [entries[0][2]]
    prev_ts = ts_to_seconds(entries[0][0])

    for ts, speaker, text in entries[1:]:
        ts_sec = ts_to_seconds(ts)
        gap = ts_sec - prev_ts
        if speaker != current_speaker or gap > gap_threshold:
            paragraphs.append({
                'speaker': current_speaker,
                'start': current_start,
                'text': ' '.join(current_text)
            })
            current_speaker = speaker
            current_start = ts
            current_text = [text]
        else:
            current_text.append(text)
        prev_ts = ts_sec

    paragraphs.append({
        'speaker': current_speaker,
        'start': current_start,
        'text': ' '.join(current_text)
    })
    return paragraphs
```

### 3. Chapter breaks

Group paragraphs into chapters by time duration (default 120 seconds):

```python
def group_into_chapters_by_time(paragraphs, chunk_seconds=120):
    chapters = []
    current_chapter = []
    current_chunk_start = ts_to_seconds(paragraphs[0]['start'])

    for para in paragraphs:
        ts_sec = ts_to_seconds(para['start'])
        if ts_sec - current_chunk_start >= chunk_seconds and current_chapter:
            chapters.append(current_chapter)
            current_chapter = []
            current_chunk_start = ts_sec
        current_chapter.append(para)

    if current_chapter:
        chapters.append(current_chapter)
    return chapters
```

### 4. Chapter naming

Analyze chapter content for topic keywords to generate meaningful titles:

```python
def generate_chapter_titles(chapters):
    topic_patterns = [
        (['world model', 'building', 'same thing', 'two videos'], 
         "Introduction: What is a World Model?"),
        (['driving', 'changing lanes', 'mirror', 'car'], 
         "The Driving Analogy"),
        (['latent', 'representation', 'compressed', 'state'], 
         "Latent States and Compression"),
        (['pixel', 'video', 'sora', 'kling', 'frame', 'genie'], 
         "Predicting Pixels: Video World Models"),
        (['muzero', 'board', 'screen', 'action', 'reward'], 
         "MuZero: Learning from Actions"),
        (['prediction', 'error', 'model predictive control'], 
         "Model Predictive Control"),
        (['color', 'visual', 'appearance', 'pushing', 'block'], 
         "The Color Change Problem"),
        (['physic', 'gymnast', 'backflip', 'momentum', 'conservation'], 
         "Physical Consistency vs Visual Realism"),
        (['agi', 'path', 'test', 'intervene', 'cause', 'effect'], 
         "Are World Models the Path to AGI?"),
    ]
    
    titles = []
    for i, chapter_paras in enumerate(chapters):
        narrator_texts = [p['text'] for p in chapter_paras if p['speaker'] == 'narrator']
        quote_texts = [p['text'] for p in chapter_paras if p['speaker'] == 'quote']
        all_text = ' '.join(narrator_texts + quote_texts).lower()
        
        best_score = 0
        best_title = None
        for keywords, title in topic_patterns:
            score = sum(1 for kw in keywords if kw in all_text)
            if score > best_score:
                best_score = score
                best_title = title
        
        if best_title and best_score >= 2:
            titles.append(best_title)
        else:
            # Fallback: first sentence of first narrator paragraph
            first_text = narrator_texts[0] if narrator_texts else "Chapter"
            first_sentence = first_text.split('.')[0].split('?')[0].split('!')[0]
            if len(first_sentence) > 60:
                first_sentence = first_sentence[:57] + '...'
            titles.append(first_sentence.replace('So ', '').replace('Um, ', ''))
    
    return titles
```

### 5. EPUB generation

```python
def create_epub(transcript_text, output_path, title, url, speaker):
    entries = parse_transcript(transcript_text)
    paragraphs = group_into_paragraphs(entries)
    chapters = group_into_chapters_by_time(paragraphs)
    chapter_titles = generate_chapter_titles(chapters)
    
    book = epub.EpubBook()
    book.set_identifier(f'yt-para-{safe_id}')
    book.set_title(title)
    book.set_language('en')
    book.add_author(speaker)
    
    # CSS: Georgia serif, justified text, blue quotes with border
    style = '''
    body { font-family: Georgia, serif; line-height: 1.6; margin: 5%; color: #1a1a1a; }
    h1 { font-size: 1.5em; margin-bottom: 0.5em; }
    h2 { font-size: 1.3em; margin-top: 1.5em; margin-bottom: 0.5em; border-bottom: 1px solid #ccc; padding-bottom: 0.3em; }
    p { margin: 0.8em 0; text-align: justify; }
    p.speaker { margin-top: 1.5em; margin-bottom: 0.3em; color: #333; font-weight: bold; font-size: 0.9em; text-transform: uppercase; }
    .quote { margin: 1em 0; padding-left: 1.5em; border-left: 3px solid #3498db; background-color: #f8f9fa; padding: 0.8em 1em 0.8em 1.5em; border-radius: 0 4px 4px 0; font-style: italic; }
    .narrator { margin: 1em 0; }
    .meta { color: #7f8c8d; font-size: 0.9em; margin-bottom: 2em; }
    '''
    
    # Build chapters with paragraph divs (no per-line timestamps)
    for i, chapter_paras in enumerate(chapters):
        chapter_title = chapter_titles[i]
        paras_html = []
        for para in chapter_paras:
            cleaned = clean_text(para['text'])
            if para['speaker'] == 'quote':
                paras_html.append(f'<div class="quote"><p class="speaker">Researcher</p><p>{cleaned}</p></div>')
            else:
                paras_html.append(f'<div class="narrator"><p class="speaker">{speaker}</p><p>{cleaned}</p></div>')
        
        chapter = epub.EpubHtml(title=chapter_title, file_name=f'chapter_{i+1:03d}.xhtml')
        chapter.content = f'<h2>{chapter_title}</h2><p class="meta">From {ts_to_hms(first_ts)} to {ts_to_hms(last_ts)}</p>{"" .join(paras_html)}'
        book.add_item(chapter)
```

## Key differences from conversation format

| Feature | Conversation (interview) | Monologue (narrated) |
|---------|------------------------|---------------------|
| Speaker alternation | Frequent (every few lines) | Rare (narrator + occasional quotes) |
| Paragraph grouping | By speaker turns | By timing gaps (>2s) |
| Timestamps | Start of each turn | Chapter-level only |
| Chapter naming | Generic ("Chapter 1") | Content-based topic titles |
| Quote styling | Speaker name + border | Blue border + italic + background |
| Best for | Podcasts, interviews | Explainers, essays, tutorials |

## Pitfalls

- **Conversation format on monologue**: Produces 1-2 giant chapters because speaker rarely changes. Always detect video type first.
- **Per-line timestamps**: Makes transcript unreadable. Only use chapter-level time ranges.
- **Generic chapter names**: "Chapter 1" is useless. Analyze content for topic keywords.
- **Missing quote styling**: `>>` lines should be visually distinct (border + italic).