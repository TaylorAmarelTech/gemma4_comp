# Structured social-media post JSON corpus

A complementary asset type to the rendered PNG screenshots in
`../static/synthetic/`. Each entry here is a **machine-readable**
representation of a social-media post / DM / channel message —
the same trafficking-pattern payload but in structured form so:

  1. Analyst-style queries (the `data_intelligence` bucket) can ask
     the LLM "given these 12 posts as JSON, cluster the recruitment-
     ad patterns" without OCR'ing screenshots.
  2. Cross-platform aggregation works (FB + TikTok + Telegram posts
     can be queried together by timestamp / author / engagement).
  3. Training-data fine-tunes can feed structured input directly.
  4. Regulator-audit prompts can ingest the same data the platform
     itself would surface in an enforcement request.

## Schema

```json
{
  "post_id":          "fb_synth_001",
  "platform":         "facebook",            // facebook|tiktok|telegram|instagram|discord|whatsapp|x|sms
  "captured_at":      "2026-04-15T10:14:00Z",
  "author": {
    "name":           "ABC Manpower (composite)",
    "handle":         "@abc_manpower_composite",
    "verified":       false,
    "account_age_days": 47,
    "follower_count": 8421,
    "synthetic":      true
  },
  "text":             "URGENT! 30 Filipina maids ...",
  "language":         "en",                   // ISO-639-1 or BCP-47
  "media": [
    {"type": "image", "url": "/static/synthetic/fb_post_ph_hk_urgent.png", "alt": ""}
  ],
  "engagement": {
    "likes":          847,
    "comments":       92,
    "shares":         128,
    "views":          null
  },
  "platform_signals": {
    "is_sponsored":   true,
    "comments_disabled": false,
    "has_external_link":  true,
    "external_link_domain": "wa.me"
  },
  "trafficking_indicators_present": [
    "fee_camouflage", "off_platform_redirection",
    "urgency_pressure", "first_come_first_served"
  ],
  "synthetic":        true,
  "license":          "CC0-1.0",
  "synthetic_disclaimer": "All persons, agencies, account names, "
                          "engagement counts are FICTIONAL. ...",
  "intended_use":     "Educational — trafficking-pattern recognition",
  "generator":        "duecare-synthetic/0.12.0"
}
```

## License

All entries are **CC0-1.0** with mandatory synthetic disclaimer.
Composite character names + reserved-for-fictional handles ensure
no real account is depicted.

## Adding your own anonymized post-JSON

1. Drop the JSON file in this folder. Filename convention:
   `<platform>_<id>.json` (e.g., `facebook_my_case_001.json`).
2. Use the same schema above. `synthetic: true` is mandatory.
3. Add a matching `data_intelligence` or `enterprise_moderation`
   prompt referencing the file via `synthetic_post: "/static/synthetic/posts/<filename>.json"`.

## Anonymization checklist

- [ ] Account name → composite tag ("ABC Manpower (composite)")
- [ ] Account handle → fictional domain or reserved prefix
- [ ] Real engagement counts → rounded synthetic numbers
- [ ] Real timestamps → shifted by random offset
- [ ] Real external links → reserved-for-fictional domains
- [ ] Real phone numbers → 555/900-prefix patterns
- [ ] Real names in comments → redacted or composite
