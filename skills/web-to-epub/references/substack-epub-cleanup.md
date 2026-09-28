# Substack EPUB Cleanup & Repair

## When to use

When you have an EPUB that was generated from Substack (either by Substack's own export or by a previous conversion) and needs to be cleaned into a proper book. Substack EPUBs carry extensive UI cruft that renders badly in e-readers.

## The Cruft

Substack EPUBs contain:

1. **`data-attrs` on images** — JSON metadata blobs that e-readers don't understand and that can break rendering
2. **`class="header-anchor-post"` on headings** — Substack's anchor-link class
3. **Nested `<div class="pencraft...">` inside headings** — the anchor button Substack injects. Structure is: `<h2>Title<div class="pencraft...">...</div></h2>`. The divs contain nested elements (button, svg, etc.) and the closing `</h2>` is AFTER all the nested divs.
4. **Duplicate headings** — sometimes a clean `<h1>Title</h1>` appears first, then a crufted `<h1 >Title<div...>...</div></h1>`
5. **Code blocks wrapped in `<div class="...code-...">`** with Substack-specific class names
6. **`fetchpriority`, `sizes`, `width`, `height`, `style`, `title` attributes on images** — Substack's responsive image attributes that interfere with EPUB CSS
7. **`class="pencraft..."` on images** — more Substack UI classes

## Cleanup Procedure

### Step 1: Extract body content

Extract the `<body>` content from each chapter XHTML. The body contains the actual article content.

### Step 2: Protect code blocks FIRST

Before any other transformation, extract `<pre>` blocks and replace with placeholders. Substack wraps code in `<div class="...code-G_k53t" data-line-numbers="true"><pre><code>...</code></pre></div>`. Save the inner `<pre><code>...</code></pre>` (cleaned of classes) and restore at the end.

### Step 3: Remove data-attrs

```python
html = re.sub(r'\s+data-attrs="[^"]*"', '', html)
```

### Step 4: Remove header-anchor-post class

```python
html = re.sub(r'class="header-anchor-post"', '', html)
```

### Step 5: Clean headings (CRITICAL)

The heading structure is: `<h2 >Title<div class="pencraft...">...</div></h2>`

A naive regex `<div[^>]*>.*?</div>` will match the FIRST `</div>` which is nested deep inside the heading, corrupting it. You must:

1. Find each heading opening tag
2. Extract the title text (everything between `>` and the first `<div`)
3. Reconstruct as `<h2>title</h2>`
4. Skip past the crufted closing `</h2>` (it comes after all nested divs)

**Pitfall**: A regex like `r'<div[^>]*>.*?</div>'` with DOTALL will consume everything up to the LAST `</div>` in the heading, not the first. The heading's `</h2>` is nested INSIDE the div structure, not at the end. You must find the title text positionally (between the opening `>` and the first `<div`), not by matching the div block.

```python
def clean_heading(match):
    tag = match.group(0)
    level = re.match(r'<h([1-6])\b', tag).group(1)
    close_tag = f'</h{level}>'
    inner = tag[tag.index('>')+1:]
    if inner.endswith(close_tag):
        inner = inner[:-len(close_tag)]
    div_pos = inner.find('<div')
    title = inner[:div_pos] if div_pos >= 0 else inner
    return f'<h{level}>{title}</h{level}>'

html = re.sub(r'<h[1-6]\b[^>]*>.*?</h[1-6]>', clean_heading, html, flags=re.DOTALL)
```

**Pitfall**: The `</h2>` that closes the heading is nested inside the pencraft divs, so a simple `find('</h2>')` from the heading start will find the WRONG one (a nested `</h2>` inside the button SVG or similar). The positional approach (find first `<div`, take text before it) avoids this.

### Step 6: Remove remaining cruft

```python
html = re.sub(r'class="pencraft[^"]*"', '', html)
html = re.sub(r'\s+class=""', '', html)
html = re.sub(r'\s+fetchpriority="[^"]*"', '', html)
html = re.sub(r'\s+sizes="[^"]*"', '', html)
html = re.sub(r'\s+width="[^"]*"', '', html)
html = re.sub(r'\s+height="[^"]*"', '', html)
html = re.sub(r'\s+style="[^"]*"', '', html)
html = re.sub(r'\s+title="[^"]*"', '', html)
```

### Step 7: Clean up whitespace

```python
html = re.sub(r'\s+', ' ', html)
```

### Step 8: Restore code blocks

Replace placeholders with the saved `<pre><code>...</code></pre>` blocks.

### Step 9: Remove duplicate H1s

If the source has a clean `<h1>Title</h1>` followed by a crufted `<h1 >Title<div...>...</div></h1>`, remove ALL H1s from the body and add your own in the chapter template.

```python
body = re.sub(r'<h1[^>]*>.*?</h1>', '', body, flags=re.DOTALL)
```

## Pitfalls

1. **Code blocks must be protected first** — if you run the generic cleanup regexes first, the code block content (which may contain `<`, `>`, `"`) gets mangled by the attribute-removal regexes.

2. **Heading cleanup is the hardest part** — the nested divs inside headings break standard regex approaches. The positional approach (find first `<div`, take text before it) is the only reliable method.

3. **Image paths** — Substack EPUBs store images as `img_ch1_xxxx.jpg` in the EPUB. When rebuilding, copy them to an `images/` directory and fix paths: `html.replace('src="img_', 'src="images/img_')`.

4. **Duplicate content** — Substack's EPUB export sometimes includes both a clean heading and a crufted heading. Remove all H1s from the body and add your own in the chapter template.

5. **Body extraction** — the article content is inside `<body>...</body>`. Extract this first, then clean.

## Output

Build a new EPUB with:
- Clean `<h1>`, `<h2>`, `<h3>` headings
- `<pre><code>` for code blocks
- `<img>` tags with CSS-controlled sizing
- `<blockquote>`, `<ul>`, `<ol>` preserved
- All Substack UI cruft removed
- Working TOC via ebooklib's EpubNcx and EpubNav