# EPUB Format Notes

## Structure

An EPUB file is a ZIP archive containing:
- `mimetype` — must be first, uncompressed
- `META-INF/container.xml` — points to the OPF file
- `OEBPS/content.opf` — package manifest with metadata, manifest, spine
- `OEBPS/toc.ncx` — navigation table of contents
- `OEBPS/*.xhtml` — the actual content documents

## ebooklib API

```python
from ebooklib import epub

book = epub.EpubBook()

# Required metadata
book.set_identifier('unique-id')
book.set_title('Title')
book.set_language('en')

# Optional metadata
book.add_author('Author Name')
book.add_metadata('DC', 'publisher', 'Publisher')
book.add_metadata('DC', 'description', 'Description')
book.add_metadata('DC', 'date', '2024-01-01')

# Content document
chapter = epub.EpubHtml(title='Chapter 1', file_name='chapter_001.xhtml')
chapter.content = '<html><body><h1>Title</h1><p>Content</p></body></html>'
book.add_item(chapter)

# Styling
style = 'body { font-family: serif; }'
nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css",
                        media_type="text/css", content=style)
book.add_item(nav_css)

# Required for navigation
book.add_item(epub.EpubNcx())
book.add_item(epub.EpubNav())

# Table of contents and spine
book.toc = [chapter1, chapter2]
book.spine = ['nav', chapter1, chapter2]

# Write
epub.write_epub('output.epub', book)
```

## Typography for Readability

- Serif fonts (Georgia, Times New Roman) for body text — best readability
- Line height 1.6–1.8 for comfortable reading
- Max-width ~40em for optimal line length
- Justified text alignment
- Color timestamps differently from body text for navigation

## Title Page Best Practices

Include:
- Video title
- Speaker name/interviewee
- Source URL
- Generation date
- Total line/exchange count

## Chapter Sizing

- Raw transcript: ~30 lines per chapter (prevents huge pages)
- Conversation: ~10 Q&A exchanges per chapter
- Both should produce multiple chapters for longer content

## Common Pitfalls

1. Missing `EpubNcx()` or `EpubNav()` — breaks navigation in readers
2. Forgetting `book.spine` — reader doesn't know page order
3. Invalid XHTML — use `<html><head></head><body>...</body></html>` structure
4. Missing `file_name` on `EpubHtml` — can't write to disk
5. Unicode issues — always use UTF-8 encoding for text files

## Windows-Specific

- `/tmp/` doesn't exist in MSYS/bash — use `$TEMP` or absolute paths
- `uv` may fail without venv — fall back to `python` directly
- `python3` may not be aliased — use `python`
- Backslashes in paths work in MSYS bash: `C:\Users\rohit\file.epub`
