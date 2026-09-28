# web-to-epub

[![skills.sh](https://skills.sh/badge/arun2565/web-to-epub)](https://skills.sh/arun2565/web-to-epub)

Convert YouTube videos, Substack transcripts, and web articles into EPUB ebooks.

## Install

```bash
npx skills add arun2565/web-to-epub
```

## Usage

```bash
python scripts/transcript_to_epub.py "https://youtube.com/watch?v=VIDEO_ID" --output out/
```

Detects monologue vs conversation format, generates named chapters, and produces clean EPUB files with proper typography.

## License

MIT
