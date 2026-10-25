---
name: normalise-to-markdown
description: Reconstruct clean, idiomatic Markdown from text that lost its structure — OCR output from a scanned or exported PDF, text copied out of Word/Google Docs/a website/Slack/an email, or anything else pasted in as a wall of oddly-wrapped, formatting-free text. Use this whenever the user pastes in messy text and asks to "make this markdown", "clean this up", "fix the formatting", "turn this OCR output into markdown", "this lost its formatting when I copied it", or hands over a .txt/.pdf-derived blob with hard line wraps, stray bullet characters, broken headings, or garbled tables. Also use when a PDF has just been read/extracted and the resulting text needs to become a proper markdown document rather than being used as-is.
---

# Normalising text into markdown

Text that has been through OCR or a copy-paste loses the structure it once
had — headings become plain lines, paragraphs get torn apart by the page's
line width, bullets turn into stray dashes or bullet glyphs, and tables
collapse into space-padded columns. The job here is not to rewrite or
improve the prose. It's forensic reconstruction: recover the structure the
original almost certainly had, and express it as clean Markdown, without
changing what it says.

## Step 1: Work out what kind of damage you're looking at

The fixes differ depending on where the text came from, so look for tells
before touching anything:

- **OCR'd PDF** — lines are wrapped at a fixed width regardless of sentence
  boundaries, words are split with a trailing hyphen at the line break
  (`docu-\nment`), the same header/footer/page-number text repeats every
  page, and there may be scanning artefacts (misread characters, `l` for
  `1`, stray `|` from a column rule). Structure like headings and lists has
  to be inferred from typographic cues that survived as capitalisation, line
  isolation, or numbering, since font size and weight rarely make it through
  OCR.
- **Copy-paste from a rendered source** — no hyphenation breaks and no
  repeating headers, but rich formatting has been flattened: headings may
  read as short standalone lines with no markup, bullets may already be `•`,
  `◦`, `‣`, or a bare `-`/`*` that a markdown renderer would show correctly
  but which needs normalising to a consistent marker, bold/italic is just
  gone, and smart quotes (`" " ' '`), em dashes, and non-breaking spaces
  (` `) are common.
- **Something already close to markdown** — pasted from a tool that half-
  understands it, so headings use `#` inconsistently, lists mix `-`/`*`/`•`,
  or spacing is uneven. Here the job is closer to linting than reconstruction.

If it's genuinely unclear which situation you're in, look at the text itself
rather than asking — the tells above are usually obvious within the first
screen of content.

## Step 2: Undo the damage before you add structure

Do this before trying to identify headings or lists, since broken line wraps
make everything downstream harder to read correctly.

- **Rejoin hard-wrapped lines.** If a line ends mid-sentence (no terminal
  punctuation, next line starts lowercase) and isn't a list item or heading,
  it's a wrap artefact — join it to the next line with a single space.
  De-hyphenate first: a trailing `-` at a line break with a lowercase
  continuation on the next line (`docu-` / `ment`) is almost always a broken
  word, not a real hyphen — remove the hyphen and rejoin. Watch for real
  hyphenated words that happen to fall at a line break (`long-\nterm`) —
  context (does `longterm` read as one word?) tells them apart from OCR
  wraps.
- **Strip running headers, footers, and page numbers.** These show up as
  short lines repeating verbatim (or with only a page number changing) at
  regular intervals through the document. They're noise, not content — drop
  them.
- **Normalise whitespace and punctuation.** Collapse runs of spaces left by
  column alignment, convert non-breaking spaces to regular ones, and convert
  smart quotes/em dashes to their plain equivalents unless the user's other
  content in the same document already uses smart typography consistently.
- **Fix obvious OCR misreads sparingly.** Only correct a character
  substitution when it's unambiguous from context (`rn` misread as `m`,
  `l`/`1`/`I` confusion). If you're not confident what the original said,
  leave it rather than guessing — inventing a plausible-looking word is worse
  than leaving a visible artefact, because it silently changes the source.

## Step 3: Reconstruct structure

Now identify what each remaining block of text actually is, and mark it up:

- **Headings.** Look for short, isolated lines that read as titles for the
  text that follows — often capitalised differently from surrounding
  prose (ALL CAPS, Title Case, or simply much shorter than a paragraph
  sentence would be), sitting alone with blank space or a topic shift around
  them. Infer a hierarchy from context (a document's title is `#`; its
  sections `##`; subsections `###`) rather than guessing at levels in
  isolation — read enough of the document first to know how many levels it
  actually has.
- **Lists.** Any bullet glyph (`•`, `◦`, `‣`, `●`, a bare `-` used
  consistently as a marker) becomes `-`. Numbered sequences (`1)`, `1.`,
  `i.`, `a)`) become `1.` markers in order — markdown renders sequential
  numbers itself, so match the source's actual numbering only if it's
  meaningfully non-sequential (e.g. skips intentionally). Preserve nesting by
  indentation depth in the source.
- **Tables.** Space- or tab-aligned columns in OCR'd or pasted text almost
  always started life as a real table. Reconstruct it as a markdown table
  with a header row and `---` separator, splitting on the consistent gaps
  between columns. If alignment is too degraded to confidently recover
  column boundaries, fall back to a plain list of the row contents rather
  than fabricating a table structure that might misattribute values to the
  wrong column.
- **Quotes and asides.** Text that's clearly set off as a quotation,
  callout, or aside (indented in the source, or introduced with something
  like "quoted below") becomes a `>` blockquote.
- **Code, commands, or literal text.** Anything meant to be read character-
  for-character — file paths, commands, code — goes in a fenced code block
  or inline code span rather than plain prose, so it isn't mistaken for
  regular text or reflowed.
- **Emphasis.** Only add `**bold**` or `*italic*` where the source gives a
  real signal it existed (e.g. a term rendered in a different case or with
  surrounding asterisks/underscores that survived the copy). Don't invent
  emphasis based on what you'd guess a human author intended — flattened
  formatting that can't be recovered should just stay plain text.

## Step 4: Normalise the markdown itself

Once structure is recovered, make the syntax consistent so the result reads
as if it were written as markdown from the start:

- ATX headings (`#`, `##`, ...), never underlined (`===`/`---`) headings.
- `-` for unordered list markers throughout, not a mix of `-`/`*`/`+`.
- One blank line between block-level elements (paragraphs, headings, lists,
  tables); no more, no less.
- No trailing whitespace, no stray hard line breaks inside a paragraph that
  should be one flowing block.
- Fenced code blocks use triple backticks with a language hint when the
  language is identifiable.

## Step 5: Check yourself before handing it back

Read the reconstructed markdown against the original once more, specifically
checking that no content was dropped, duplicated, or reworded in the
process — the goal is structure recovery, not editing. If large sections
were ambiguous (a table you weren't confident reconstructing, a heading
level you had to guess at), say so briefly rather than presenting a fully
confident result that papers over the uncertainty.

Deliver the result as an actual markdown file if the source was a
substantial document (more than a few paragraphs) or if the user is going to
reuse it elsewhere; for a short snippet pasted directly into the
conversation, a markdown-formatted reply is enough.
