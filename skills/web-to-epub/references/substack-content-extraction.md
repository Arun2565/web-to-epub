# Substack Article Content Extraction

## Purpose

Extract ONLY the article content from a Substack page, stripping all promotional UI, navigation, and marketing material. User's explicit requirement: "take only what is needed for the epub, i.e. avoid Subscribe and last similar articles, etc promotional content."

## Article Boundaries

### Start: First Article Heading

The article starts at the first `# ` or `## ` heading that is NOT a site name (e.g., `# ![Decoding AI Magazine](...)`). Skip all lines before this:
- `[![Site Logo](...)]` site header image
- `# ![Decoding AI Magazine](...)` site title
- `SubscribeSign in` / `Subscribe` / `Sign in`
- User avatar images (`![User's avatar](...)`)
- `Discover more from...` description paragraphs
- Subscriber counts (`Over 44,000 subscribers`)
- `Already have an account? Sign in`
- `By subscribing, you agree...` / `Terms of Use` / `Privacy Policy`

### End: First Promotional Marker

The article ends at the FIRST of these markers (scanning forward from start, not backward from EOF):

**Primary end markers (stop here):**
- `### Ready for more?` / `ready for more?`
- `#### Subscribe to` / `subscribe to decoding`
- `#### Discussion about this post` / `discussion about this post`
- `commentsrestacks`
- `enjoyed the article?` (and its continuation `_The most sincere compliment...`)
- `restacks` (standalone line)
- `see all` (standalone line)
- `toplatestdiscussions` (case-insensitive, no punctuation)

**Secondary end markers (also stop):**
- Course promotion paragraphs: `go from agent user to agent builder`, `master the foundations of ai agents`, `start here`, `free agent ai engineering guide`
- Sponsor banners: `_Thanks again to [Opik](...) for sponsoring this article._`
- Author avatar images at footer (after article content)
- `Leave a comment` links
- `CommentsRestacks`

**Tertiary end markers (also stop):**
- `Similar articles` / `Related articles` / `You might also like` / `Recommended for you`
- Any line containing `subscribe` after the article conclusion
- Any line containing `restacks` as a standalone word

## Content to Preserve

- All headings (`# ` through `#### `) that are part of the article structure
- All paragraphs of article text
- All images (diagrams, charts, screenshots) — strip only avatar images
- All code blocks (``` fenced blocks)
- All lists (ordered and unordered)
- All blockquotes
- All links (both internal series links and external references)
- References sections (`## References`)
- Author bio line (e.g., `[Paul Iusztin](...)`)
- Closing question to readers (e.g., `_What's your opinion?..._`)
- `---` / `***` horizontal rules that separate sections within the article

## Content to Strip

### Header cruft
- Site logo/name links
- Subscribe/Sign in buttons
- User avatars (`avatar` in URL)
- Subscriber counts
- Terms of Use / Privacy Policy footer links

### Promotional footers
- `Enjoyed the article? The most sincere compliment is to share our work.`
- `Go from agent user to agent builder.` / `Master the foundations of AI agents...`
- `Start here` / `Free Agent AI Engineering Guide`
- Course promotion links
- Sponsor thank-you paragraphs and banners
- `Try Opik for free here` / `Quick start guide`

### Navigation cruft
- `TopLatestDiscussions`
- `See all`
- `8 Restacks` / `Restacks`
- `CommentsRestacks`
- Related article previews
- `PreviousNext`
- Comment sections (`#### Discussion about this post`, individual comments)
- Like counts (`44 Likes`)
- `Share` links

## Implementation Notes

### Finding end: forward scan from start, not backward from EOF

The article may contain `subscribe` within the text (e.g., in a course description within the article body). Scanning backward from EOF risks cutting at the wrong place. Instead:

1. Find the start (first real heading)
2. Scan forward from start
3. At each line, check against the marker list
4. The FIRST marker hit is the end

### Multi-line promotional blocks

Some promotional content spans multiple lines (e.g., the "Enjoyed the article?" paragraph followed by italic text). Use a state machine: when you hit a primary marker, set `skip_until_next_heading = True` until the next `#` heading is encountered (which would be a legitimate section like `## References`).

### Avatar image detection

Skip images where the alt text or URL contains `avatar`. These are Substack UI elements, not article content.

### Course promotion detection

Lines containing `go from agent user to agent builder`, `master the foundations of ai agents`, `start here`, or `free agent ai engineering guide` are Substack marketing copy, not article content.

### Sponsor detection

Lines matching `_Thanks again to [Brand](url) for sponsoring this article._` and subsequent banner images/links are promotional and should be stripped.

## Verification

After extraction, verify:
- No promotional markers remain in output (grep for subscribe, restacks, enjoyed, start here, ready for more)
- Article ends naturally (references, author bio, or closing question)
- Headings are complete (H1 title + H2 sections)
- Images are present (diagrams, charts) but no avatars
- Links work (both internal series and external references preserved)
