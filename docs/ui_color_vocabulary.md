# UI color vocabulary — DueCare workbench

Captures the color semantics applied across the workbench pages so
future edits stay consistent. Live as of `ui-polish-2026-05-23`.

## The four-color palette

Every UI element on the workbench uses one of four semantic colors.
If a new element doesn't fit into this scheme, that's a smell — either
the element is doing too much or the scheme needs a documented
addition.

| Color | OKLCH | Semantic | Where it shows |
|---|---|---|---|
| **Teal** | `oklch(0.52 0.08 195)` | Gemma 4 active / primary action | Primary buttons, Gemma 4 marks, top-bar tally badge, synthesis callout, chevron pulse, activity-log `[GEMMA 4]` prefix, contextual-media tile when complete |
| **Amber** | `oklch(0.78 0.10 45)` (border) / `oklch(0.40 0.16 25)` (text) on `oklch(0.97 0.025 25)` paper | Destructive / deferred / warning | Cancel / Abandon / Reset / Clear buttons (`wb-btn-destructive`, `.composer .btn.destructive`), deferred queue tiles, "Gemma 4 unavailable" / "deferred" marks |
| **Green** | `oklch(0.62 0.10 155)` (border) / `oklch(0.32 0.07 155)` (text) | Done / safe / privacy-OK | Completed workflow steps (`.complete` class), `is-done` pills, trust-boundary banners, `oklch(0.92 0.06 155)` for the soft fill |
| **Red** | `oklch(0.55 0.18 25)` solid / `oklch(0.72 0.16 25)` text | Error / fallback | Error banners, `wb-error` cards, fallback route badges, `dc-log-tag-err` log rows |

Neutrals (paper / ink / line) come from CSS custom properties in
`_chrome.css` (`--paper`, `--ink`, `--ink-2`, `--line`, etc.).

## Hard rules

1. **Teal means Gemma 4.** Don't use teal for any other purpose. If
   a non-Gemma element needs to look "important," use the primary-button
   style (also teal but explicitly tagged primary). Reviewers and judges
   have been trained to see teal = Gemma; breaking that costs clarity.

2. **Amber means "something destructive or deferred."** Never use amber
   for a benign secondary action. If you want a soft secondary, use the
   paper-on-line outline (`wb-btn-secondary`, `composer .btn.secondary`).

3. **Green is reserved for done / safe.** A completed step gets the
   green left-border. The trust-boundary banner uses soft-green. Don't
   use green for in-progress or partial states (use teal-pulse or
   amber-pulse).

4. **Red is for genuine errors only.** Fallback paths that intentionally
   degrade gracefully should use amber, not red. Red implies "something
   broke; investigate."

## Standard combinations

When you need to add a new UI element, pick one of these standard
combinations rather than inventing a new color pairing:

- **Teal callout box** (used by the synthesis answer block, the
  case-theory render, and the contextual-media tile when in
  `Gemma 4 reviewed` state):
  ```css
  background: oklch(0.97 0.025 195);
  border: 1px solid oklch(0.78 0.06 195);
  border-left: 4px solid oklch(0.52 0.08 195);
  ```

- **Amber destructive button:** see `.wb-btn-destructive` in
  `_chrome.css`.

- **Green completion accent:** `border-left: 4px solid oklch(0.62 0.10 155);`
  on `.complete` workflow steps.

- **Red error banner:** see `.wb-error` in per-page CSS (consistent
  across pages).

## Animations vocabulary

| Animation | Where | Meaning |
|---|---|---|
| `wbGemmaTallyPulse` | Top-bar tally badge | A Gemma 4 call just completed; tally count incremented |
| `wbGemmaTallyInflight` | Top-bar tally badge | An inference is currently running on the kernel |
| `wbStepFlowPulse` | `wb-step-flow ↓` chevron | The next workflow step is the currently-active step |
| `dc-pillpulse` | `dc-pill.is-running .dot` | A workflow step is currently active |

All four use the teal accent color so the animation vocabulary stays
consistent with the static color semantics.

## When in doubt

Ask: "what does this element MEAN to a first-time judge?"

- If it means "Gemma 4 did something" — teal.
- If it means "click me to undo / cancel / start over" — amber destructive.
- If it means "this is finished, the data is safe" — green.
- If it means "something broke" — red.

If the answer is "none of the above," it's probably a neutral element —
use the paper / ink / line palette without a semantic accent.

## Files where the palette is defined

- `packages/duecare-llm-chat/src/duecare/chat/static/_chrome.css` —
  shared `.wb-btn-destructive`, `.dc-pill.*`,
  `.dc-wb-gemma-tally-*`, `.wb-step-flow*`,
  `.dc-log-event-gemma`, `.dc-log-tag-gemma`.

- Each workbench page's `<style>` block — re-declares
  `.wb-btn-primary` and `.wb-btn-secondary` with page-specific padding
  but the teal hue is identical (`oklch(0.52 0.08 195)`).

- `configs/duecare/design_tokens.yaml` (referenced in
  `.claude/rules/60_notebook_presentation.md`) — source of truth for
  civic-teal accent + ember privacy-boundary color.

## How this doc relates to the broader project palette

The civic-teal + warm paper palette here is a workbench-specific
restriction of the full DueCare brand palette documented in
`.claude/rules/60_notebook_presentation.md`. The notebook palette adds
**ember** (`oklch(0.58 0.14 45)`, used only as a privacy-boundary
indicator on the marketing site / notebooks) and **warn**
(`oklch(0.65 0.10 80)`, used for non-destructive cautions). The
workbench intentionally collapses ember and warn into a single
amber-destructive style because the workbench audience already has
a "deferred / cancel / destructive" mental model and adding more
yellow shades would muddle it.
