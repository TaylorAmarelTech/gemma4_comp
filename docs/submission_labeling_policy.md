# Client submission labeling policy

DueCare should support richer labels on client-to-hub submissions, but labeling must remain privacy-preserving and controlled by the submitting client. The central server should receive sanitized information objects plus explicit metadata about who is sharing, what can be displayed, and which labels were manually asserted versus automatically suggested.

## Design goal

Let a worker tool, NGO deployment, platform integration, or regulator share useful context without forcing attribution. A submission can be anonymous, pseudonymous, organization-tagged, region-tagged, corridor-tagged, sector-tagged, or fully private to a consortium, depending on consent and deployment policy.

## Attribution modes

| Mode | What the hub stores | Public display default | Best for |
|---|---|---|---|
| Anonymous | No organization identifier; only coarse metadata allowed by policy. | Aggregate only. | Worker-controlled tools, sensitive pilots. |
| Pseudonymous deployment | Stable tenant hash or deployment key, not a public org name. | Aggregate by cohort after threshold checks. | NGO pilots that want trend continuity without public attribution. |
| Organization-tagged | Organization registry ID and display name chosen by the submitter. | Organization name hidden unless `public_attribution=true`. | Trusted NGO/regulator/platform submissions. |
| Verified organization | Organization ID verified out-of-band by the hub operator. | Can show verified badge when consented. | Formal partners, benchmark/result submissions, pack maintainers. |
| Public-source only | Source URL and public-document metadata; no private submitter needed. | Source citation can be displayed. | Laws, advisories, public court records, policy updates. |

## Label sources

Every label should carry a source and confidence, not just a value.

| Source | Meaning | Rule |
|---|---|---|
| `manual_submitter` | A user or admin explicitly selected the label before sending. | Highest priority, but still validated against allowed values. |
| `tenant_default` | A local deployment default, such as an NGO's home country or corridor focus. | Applied only if the tenant has opted in. |
| `local_model_suggested` | Local Gemma 4 or deterministic parsing suggested region, sector, language, or corridor. | Must be reviewable before publishable sharing. |
| `server_inferred` | The hub inferred metadata from sanitized text or headers. | Never used to add public attribution; only for internal triage. |
| `verified_registry` | The hub matched an organization or partner registry record. | Can verify the submitter, not the underlying case facts. |

Automatic detection should **suggest** labels, not silently upgrade a submission from anonymous to attributed. The safe default is: manual labels can override automatic suggestions; automatic suggestions can lower confidence or route for review; they cannot expose an organization, exact location, or individual.

## Recommended metadata envelope

```json
{
  "submission_id": "hash_receipt_or_uuid",
  "submission_type": "case_pattern_observation",
  "visibility": "private_review",
  "attribution_mode": "pseudonymous_deployment",
  "submitter": {
    "tenant_id_hash": "sha256:...",
    "organization_registry_id": null,
    "display_name": null,
    "public_attribution": false
  },
  "labels": [
    {
      "key": "region",
      "value": "Southeast Asia",
      "source": "manual_submitter",
      "confidence": 1.0,
      "public_safe": true
    },
    {
      "key": "corridor",
      "value": "Philippines -> Gulf",
      "source": "local_model_suggested",
      "confidence": 0.78,
      "public_safe": false
    },
    {
      "key": "sector",
      "value": "domestic work",
      "source": "tenant_default",
      "confidence": 0.9,
      "public_safe": true
    }
  ],
  "consent": {
    "share_sanitized_object": true,
    "share_aggregate_trends": true,
    "allow_recontact": false,
    "allow_training_use": false,
    "allow_public_display": false
  }
}
```

## Visibility states

| Visibility | Server behavior |
|---|---|
| `local_only` | Nothing is sent to the hub. The local deployment may still produce a local hash receipt. |
| `private_review` | Hub stores the sanitized object for authorized reviewer/curator queues only. |
| `consortium_private` | Shared with a named trusted consortium or regional working group. |
| `aggregate_only` | Used only in thresholded trend counts; no row-level display. |
| `benchmark_public` | Safe benchmark/result metadata can be published after validation. |
| `pack_public` | Approved public-source facts or sanitized knowledge objects can enter a Knowledge Pack. |

## Privacy guardrails

- Raw worker chats, case files, IDs, contact details, and private documents stay on the worker device or trusted NGO hardware unless an authorized user explicitly creates a sanitized submission.
- Exact addresses, phone numbers, passport numbers, case IDs, and personal names never become labels.
- Region labels should be coarse enough to avoid re-identification; exact city labels require explicit public-source provenance or a trusted-private visibility state.
- Public trend displays should enforce minimum cell counts before showing combinations such as organization + region + sector + corridor.
- The server should reject submissions where auto-detected PII appears in labels, metadata, or sanitized object fields.
- Organization identity should be separable from case content: the hub can verify the sender without making the sender public.

## UX recommendation

The submission UI should show a two-column review step before upload:

1. **What will be shared:** sanitized object preview, labels, consent choices, visibility, hash receipt.
2. **What stays local:** raw text, images, private documents, contact details, detector-redacted fields.

Manual labels should be editable chips. Automatic labels should appear as suggestions with confidence, for example: `region: Southeast Asia (suggested, 78%)`. The final submit button should be disabled until the user confirms the no-raw-case consent statement.

## Why this helps the benchmark

The same envelope can support Kaggle benchmark/result sharing. Researchers can submit model results with attribution set to anonymous, pseudonymous lab, verified organization, or public model-maintainer. The benchmark can rank models while preserving provenance: `git_sha`, `dataset_version`, `scorer_version`, `model_id`, `organization_registry_id` when consented, and visibility policy.
