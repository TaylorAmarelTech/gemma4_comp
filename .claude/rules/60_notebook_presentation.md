# Notebook presentation — Kaggle-safe styling and output rules

> Auto-loaded by Claude Code at the project memory level. Applies to
> every build script in `scripts/build_notebook_*.py` and every cell
> those scripts emit into `notebooks/*.ipynb` and
> `kaggle/kernels/*/*.ipynb`.

The shared runtime helpers live in `scripts/_notebook_display.py`
(use `DISPLAY_BOOTSTRAP` at the top of any cell that needs them). The
rules below are the presentation contract those helpers implement.
Follow them verbatim or patch both the rule and the helper at the same
time.

## Hard rules

### Never truncate displayed text

- No `text[:N]...`, `response[:200]`, `prompt[:120]` on anything the
  reader is supposed to understand. Show the full content.
- Never save a `response_preview` / `prompt_preview` field in a
  downstream JSON artifact. The preview field is lossy by design and
  makes every downstream notebook re-truncate or re-read the full file.
- The only acceptable truncation is at the *output boundary* — a
  one-line progress print during a long run may abbreviate the
  category label for alignment. Never the prompt or the response.
- When pandas would truncate, call
  `register_pd_display_defaults()` (from the shared helpers) or
  `pd.set_option('display.max_colwidth', None)` before the
  `display()` call.

### Prefer pandas Styler and Markdown over raw HTML

- Tables: `pandas.DataFrame.style.apply(...).format(...).bar(...)`.
  Renders as a real HTML table in the Kaggle saved-output viewer.
- Prompt + response blocks: `IPython.display.Markdown` with triple-
  backtick fenced code blocks. Fenced code blocks preserve the text
  verbatim and render identically across Kaggle viewer, Kaggle run
  mode, Jupyter, Colab, VS Code, and nbviewer.
- Banners and callouts: `show_callout(text, kind=...)` from the shared
  helpers. One-level inline HTML, no flex, no overflow.
- Use `show_headline`, `show_distribution`, `show_table`,
  `show_prompt_response`, `show_compare_table`,
  `show_stat_cards` (colored tile row), and
  `show_pipeline_diagram` (horizontal flow) from
  `_notebook_display.py` rather than re-inlining HTML.
- **Break up prose walls.** If a markdown cell has more than ~800
  characters of uninterrupted text, replace part of it with a
  `show_stat_cards` row (key numbers), a `show_pipeline_diagram`
  (step-by-step flow), or a pandas Styler table. Text dense enough
  that a judge scrolls past it is text that isn't doing its job.

### Kaggle viewer banned patterns

The Kaggle public viewer sanitizes HTML. The following patterns get
stripped, collapsed, or silently reformatted and must not appear in
any emitted cell:

- `display: flex` and `flex-wrap`. Use `pandas.Styler` tables instead.
- `max-height: ...; overflow: auto`. The overflow is removed; giant
  unscrollable regions result. Render full-height or use a
  `pandas.Styler` table which handles width/height natively.
- `<script>`. Stripped for security. Never emit one; use Plotly
  (which has its own safe JS injection path) for interactivity.
- `position: fixed|absolute|sticky`. Stripped.
- External stylesheets (`<link rel="stylesheet">`). Use inline
  `style=` attributes only.
- Custom fonts via `@font-face`. Use system font stacks.

### Accepted HTML patterns

These render reliably in the Kaggle saved-output viewer and match the
existing `HEADER_TABLE` pattern already used across the suite:

- `<table>`, `<thead>`, `<tbody>`, `<tr>`, `<th>`, `<td>` with inline
  `style=`.
- `<div>`, `<span>`, `<code>`, `<b>`, `<i>`, `<u>`, `<br>`.
- Inline `style=` with: `background`, `background-color`, `color`,
  `border`, `border-left`, `border-radius`, `padding`, `margin`,
  `font-family`, `font-size`, `font-weight`, `font-style`,
  `text-align`, `white-space: pre-wrap`, `line-height`.
- `<a href="...">` internal anchors for tables of contents.

## Palette

Use the palette defined in `scripts/_notebook_display.py` and
`HEADER_TABLE` (already used across the 000-189 notebooks). Do not
introduce new colors:

| Role | Hex | Use |
|---|---|---|
| primary | `#4c78a8` | primary bars, main CTA links |
| success | `#10b981` | refusals, passing cases, kept rows |
| warning | `#f59e0b` | partial-match, "neutral" band |
| danger  | `#ef4444` | harmful content, enables-harm flag, dropped rows |
| info    | `#3b82f6` | informational banners, neutral callouts |
| muted   | `#6b7280` | secondary text, category tags |

Background pairs (`bg_success`, `bg_warning`, `bg_danger`, `bg_info`)
are light-tinted versions meant to pair with the same-name accent on a
border.

## Structure every notebook must follow

1. **HEADER** (markdown)
   - One-line headline sentence.
   - HEADER_TABLE with inputs / outputs / prerequisites / runtime /
     pipeline position (existing pattern — do not redesign).
   - "Reading paths" / "Reading order" bullet list.
   - **Table of contents** with anchor links to every numbered section.
2. **PREVIEW** (code, Section 0) — runs first, no dependencies.
   - A short static example of what the notebook produces. Full text,
     no truncation. Lets a reader understand the purpose without
     executing the model-load cell.
3. **Numbered sections** starting at §1, each with an `<a id="..."></a>`
   anchor matching the TOC.
4. **Worst / most-informative rows first**. When displaying a sorted
   table of outputs, surface the extreme cases at the top so a reader
   scrolling for three seconds sees them without pagination.
5. **Summary + next-steps** markdown cell at the bottom, linking back
   to the relevant section conclusion and the index.

## Artifacts and file outputs

- Save full responses and full prompts in every JSON artifact. No
  `response_preview` field.
- When downstream notebooks only need the score + grade, have them
  re-read the full artifact and do their own projection. Do not
  pre-truncate in the source.
- Every artifact writer prints the output path, total byte size, and
  a one-line summary of what downstream notebooks will see.

## Anti-patterns seen in the wild (do not repeat)

- `print(f'  {p["text"][:150]}...')` — use `show_table` with
  `wrap_cols=['text']`.
- `response_preview = response_text[:300]` saved alongside
  `response_full` — drop the preview field.
- `response.text[:80]` in a progress-print line alongside a grade
  tag — keep the grade tag, drop the text preview (the score is the
  useful signal, the snipped text is noise).
- `<div style="max-height: 200px; overflow: auto">` — stripped in the
  Kaggle viewer, produces an unreadable giant block.
- `<div style="display: flex; flex-wrap: wrap">` — collapses to
  stacked blocks in the Kaggle viewer. Use `show_table` with the
  side-by-side columns as pandas columns.

## Enforcement

- A grep over `scripts/build_notebook_*.py` for the strings
  `[:200]`, `[:150]`, `[:300]`, `_preview`, `display: flex`,
  `max-height` should return zero **display** hits. Dedupe-hash uses
  like `hashlib.md5(text[:200])` and near-duplicate prefix matching
  like `text[:100].lower()` are NOT display uses and are allowed.
  The grep is a triage tool, not a hard gate; inspect each hit.
- Recommended enforcement grep (run from the repo root):
  ```bash
  grep -n -E '\[:(80|100|120|150|200|300)\]|response_preview|prompt_preview|display:\s*flex|max-height:\s*[0-9]+px;\s*overflow' scripts/build_notebook_*.py
  ```
- New build scripts that fail the grep should be caught in review.
- When updating an existing build script, apply these rules as part
  of the edit; do not defer.
