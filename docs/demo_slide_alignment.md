# Demo Slide Alignment Checklist

This note keeps the recording deck aligned with the public hub copy in
`apps/duecare-ai.com` and the focused Kaggle runtime in
`kaggle/02-live-demo`.

## Canonical Story

DueCare is a local Gemma 4 harness ecosystem for migrant-worker safety. It is
not a single chatbot and not a raw central case-management system.

The demo story should move in this order:

1. Scale problem: exploitation persists because content moderation, case
   analysis, worker support, and research workflows are fragmented.
2. Solution diagram: one local harness ecosystem supports several channels.
3. Gemma 4 role: open-weight, efficient, tool-capable, fine-tunable model engine.
4. Content moderation: pre-publish or queue-time screening for exploitative UGC.
5. Case analysis: bulk file review, typed edges, evidence graph, complaint draft.
6. Worker support: phone-first and offline-capable when the selected
   model build and local packs are available.
7. Research: corridor trends, recurring agencies, accounts, and verified facts.
8. Anonymized knowledge sharing: reviewed facts can improve packs without
   sending raw case files to the public hub.

## Terminology

Use these phrases in new demo and website copy:

- `case analysis`, not `case intake`, when describing the product lane.
- `offline-capable` or `on-device-oriented`, not a blanket claim that every
  deployment works offline.
- `public hub`, not `central case system`.
- `anonymized signals`, `public-source proposals`, and `reviewed knowledge
  facts`, not raw worker case uploads.
- `draft`, `suggestion`, or `routing suggestion`, not automatic filing or
  automatic contact with employers, NGOs, or regulators.

Keep these phrases where they describe the privacy boundary:

- `No raw case intake`
- `signal intake`
- `public-source proposal intake`

Those are data-boundary/API terms and should not be rewritten to `analysis`.

## Source Files

- Website source of truth:
  - `apps/duecare-ai.com/app/templates/index.html`
  - `apps/duecare-ai.com/app/templates/use-cases.html`
  - `apps/duecare-ai.com/app/templates/why-gemma.html`
  - `apps/duecare-ai.com/README.md`
- Recording deck:
  - `packages/duecare-llm-server/src/duecare/server/static/slides.html`
- Live demo runbook:
  - `kaggle/02-live-demo/README.md`

## Validation

Before recording, run:

```bash
python -m pytest packages/duecare-llm-server/tests/test_slides_surface.py -q
python -m pytest apps/duecare-ai.com/tests -q
```

Then manually review `/slides` at the live demo URL. The bottom-right corner
must remain clear for the presenter camera overlay, and visible recording
controls should stay out of the captured frame.
