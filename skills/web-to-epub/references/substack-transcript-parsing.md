# Substack Transcript Parsing

## Source Format

Substack posts (Dwarkesh Podcast) embed transcripts as HTML within `<article>` tags:

```html
<article>
  ...
  <h3>00:00:00 - Agents get kicked off</h3>
  <p><strong>Dwarkesh Patel</strong></p>
  <p>Today I'm chatting with...</p>
  <p><strong>Ajeya Cotra</strong></p>
  <p>OpenAI kicks off tens of thousands...</p>
  <h3>00:06:45 - Self-sacrificing behavior</h3>
  ...
</article>
```

## Parsing Strategy

1. **Find article**: regex `<article[^>]*>(.*?)</article>` with DOTALL
2. **Find transcript start**: `article.find('Transcript')` — the word "Transcript" appears as a section marker
3. **Split by h3**: `re.split(r'(<h3[^>]*>.*?</h3>)', article, flags=re.IGNORECASE|re.DOTALL)`
4. **Parse h3 headers**: extract timestamp `(\d{2}:\d{2}:\d{2})` and title
5. **Parse paragraphs**: `re.findall(r'<p[^>]*>(.*?)</p>', part, re.IGNORECASE|re.DOTALL)`
6. **Detect speakers**: `<strong>Name</strong>` or `<b>Name</b>` at start of paragraph
7. **Map names**: "Dwarkesh" → "Dwarkesh Patel", "Ajeya" → "Ajeya Cotra", etc.

## End Markers

Stop parsing when hitting:
- "Ready for more?"
- "188 Likes" / "188"
- "#### Discussion about this video"
- "CommentsRestacks"
- "Share post"
- "Subscribe"

## Filtering

Skip paragraphs containing:
- Sponsor links (janestreet.com, cursor.com/dwarkesh, antithesis.com)
- "Watch on" / "Listen on" links
- Navigation elements
- Empty paragraphs

## Output

Each section becomes an EPUB chapter with:
- `<h2>Section Title</h2>` header
- `<p><b>Speaker:</b> text</p>` for each turn
- Speaker name bolded, text justified
