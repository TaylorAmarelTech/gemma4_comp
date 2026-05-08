# Synthetic-evidence assets

Image assets bundled in the chat-package wheel for use with the
`image_prompts` example bucket. The chat UI auto-attaches one of
these images when the user clicks an example whose JSON entry
declares a `synthetic_image` field.

## What's in here

Two kinds of assets, treated identically by the UI:

1. **Auto-generated synthetics** — produced by
   `scripts/generate_synthetic_evidence.py` via Pillow templating.
   No real persons, agencies, account numbers, or phone numbers.
   Composite character names ("Maria Composite", "Ramesh Composite")
   and reserved-for-fictional-use phone-number patterns
   (555/900-prefix). Each image has a visible
   "SYNTHETIC — TRAINING USE ONLY" watermark.

2. **Manually-anonymized real assets** — images sourced from real
   trafficking-evidence material that have been anonymized for
   publication safety. Faces blurred / cropped, names redacted,
   license plates and identifying numbers blacked out, employer
   names + bank-account fragments scrubbed.

## Adding your own anonymized image

1. Place the PNG / JPG in this folder. Filename must be unique and
   start with the asset kind:
   ```
   receipt_<id>.png       — recruitment receipt
   contract_<id>.png      — employment contract page
   fb_post_<id>.png       — Facebook recruitment post
   tiktok_<id>.png        — TikTok screenshot
   whatsapp_<id>.png      — WhatsApp chat
   telegram_<id>.png      — Telegram channel / chat
   passport_<id>.png      — passport stamp / visa page
   marketplace_<id>.png   — marketplace listing
   wallet_<id>.png        — crypto wallet screenshot
   evidence_<id>.png      — generic evidence / receipt
   ```

2. Drop a sidecar JSON next to it (`<same-stem>.json`):
   ```json
   {
     "image_id":     "<same as filename stem>",
     "image_kind":   "<one of: recruitment_receipt | contract_page | social_media_facebook | social_media_tiktok | social_media_whatsapp | social_media_telegram | passport_stamp | marketplace_listing | crypto_wallet | other_evidence>",
     "description":  "<one-line description of what's in the image>",
     "license":      "CC0-1.0 / CC-BY-4.0 / your-anonymization-disclaimer",
     "source":       "manually anonymized / synthesized / your attribution",
     "synthetic":    true,
     "synthetic_disclaimer": "<paragraph explaining anonymization steps + any caveats>",
     "intended_use": "Educational — trafficking-pattern recognition for AI safety-harness demonstrations",
     "generated_at": "<ISO-8601 timestamp>"
   }
   ```

3. Add an `image_prompts` entry to `_examples.json` referencing the
   asset path:
   ```json
   {
     "id": "v0_xx_image_my_case",
     "bucket": "image_prompts",
     "category": "<existing image category>",
     "subcategory": "...",
     "image_hint": "what the image shows",
     "synthetic_image": "/static/synthetic/<filename>.png",
     "text": "the prompt the user types",
     "sector": "...", "corridor": "...", "difficulty": "...",
     "ilo_indicators": [...]
   }
   ```

4. Re-build the wheel (`py -3.10 -m build --wheel ...`) — pyproject's
   `static/**/*` glob picks up everything in this folder
   automatically.

## Anonymization checklist (manual assets)

Before placing a manually-anonymized asset:

- [ ] All visible faces fully blurred OR replaced with synthetic
      equivalents OR cropped out (not just pixelated — pixelation
      is reversible by some methods).
- [ ] All visible person names + signatures redacted with a solid
      black box (NOT blurred — blur preserves recoverable text).
- [ ] All visible phone numbers, account numbers, passport numbers,
      ID numbers redacted with solid black box.
- [ ] All visible business names + logos either replaced with a
      generic stand-in ("ABC Manpower (composite)") or pixel-painted
      out.
- [ ] Image metadata (EXIF GPS, original timestamp, camera serial)
      stripped via `exiftool -all= image.png` or equivalent before
      adding to repo.
- [ ] If sourced from a public document collection (court filings,
      NGO reports), keep the case-citation reference in the sidecar
      `source` field.

## License declaration

All assets in this folder ship under **CC0-1.0** (public-domain
dedication) UNLESS the sidecar JSON's `license` field declares
otherwise. The CC0 declaration applies only to the asset's
representational layer — the underlying real-world facts (statutes,
ILO indicators, agency-pattern descriptions) live in their own
copyright regimes.

The synthetic-disclaimer in every sidecar is a load-bearing legal
notice. Downstream reusers MUST preserve the disclaimer or replace
it with an equivalent acknowledgement when reformatting.

## Risk register

- **Misuse for fraud:** synthetic receipts could be re-used as real-
  looking forgeries. Mitigations: visible watermark, fictional names
  in plain text, blocky template aesthetic that no real agency
  would issue.
- **Trauma:** users encountering compound-extraction or
  passport-retention images without context can be triggered. The
  examples-modal renders a `📎 Attach an image` banner before
  loading, surfacing the image's nature ahead of attaching.
- **Data poisoning:** a malicious contributor could drop in a
  poisoned image masquerading as anonymized evidence. Mitigation:
  the chat package only RENDERS bundled images; the model only
  receives them when a user explicitly attaches one. New
  contributions go through git PR review.
