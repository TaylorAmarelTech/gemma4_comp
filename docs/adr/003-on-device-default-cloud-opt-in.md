# ADR-003: On-device default; cloud routing opt-in for Android

- **Status:** Accepted
- **Date:** 2026-04-30
- **Deciders:** Taylor Amarel

## Context

The Duecare Journey Android app (`duecare-journey-android`) targets
migrant workers — a population whose threat model includes:

- Coercive recruiters who may inspect the worker's phone
- Hostile employers who may confiscate the phone
- Network operators (in some jurisdictions) who may surveil messages
- The worker's own family (in some cases) who may pressure disclosure

For this audience, "all data on device" is a load-bearing privacy
guarantee, not a marketing claim.

But: in v0.5 we shipped Gemma 4 E2B as the default on-device model,
and the litert-community URL we hard-coded started returning 404.
Workers who couldn't download the model also couldn't use the chat
surface — which broke the whole app's value prop.

Two options:
1. Soft-fail to canned responses (the v0.5 behavior — judges saw
   stub text instead of real chat)
2. Add a cloud-routing fallback so the chat surface works
   immediately while the on-device download retries

## Decision

**On-device is the default. Cloud routing is opt-in via Settings
→ Cloud model.**

The `SmartGemmaEngine` routing chain in v0.6+ is:
1. Cloud (if a worker has explicitly configured a cloud endpoint
   in Settings) — Ollama / OpenAI-compatible / HF Inference formats
2. MediaPipe on-device Gemma (if model is downloaded + loadable)
3. Stub (canned legal-citation responses)

Each tier falls through to the next on Flow exception, so the UI
never sees a thrown exception in normal operation.

The Settings tab spells out the privacy implication of enabling
cloud routing in plain language before saving.

## Alternatives considered

- **Cloud as default.** Rejected because it breaks the privacy
  guarantee for every worker who doesn't read the privacy doc.
- **Cloud only when on-device fails.** Rejected because it's a
  silent privacy downgrade — the worker doesn't know their prompts
  are leaving the device.
- **Single cloud provider** (e.g., always Ollama). Rejected because
  it forces operator's choice on the worker. The OpenAI-compatible +
  HF Inference formats let the operator pick their preferred backend
  per the workforce they support.

## Consequences

**Positive:**
- v0.6 chat works on first launch even if the on-device download
  is broken — closes the v0.5 regression
- Workers who don't trust the cloud endpoint can keep on-device-only
  by leaving the Cloud model section empty
- NGO sysadmins can stage devices with their own cloud endpoint
  (e.g., a Render-deployed server they trust) before handing the
  phone to a worker
- Three cloud formats supported (Ollama / OpenAI / HF Inference)
  means no operator is locked in

**Negative:**
- Workers who DON'T read the privacy section may not realize their
  prompts are leaving the device once they enable cloud routing.
  Mitigated by the Settings copy + the in-app banner.
- Dual code path (cloud HTTP vs on-device MediaPipe) means more
  edge cases (timeout, network change, auth failure)
- Future feature work (e.g., per-prompt redaction) must be applied
  at both code paths

## References

- [`docs/deployment_topologies.md`](../deployment_topologies.md)
  Topology D vs E
- Android sibling repo:
  `app/src/main/java/com/duecare/journey/inference/SmartGemmaEngine.kt`
- [`docs/considerations/THREAT_MODEL.md`](../considerations/THREAT_MODEL.md) Boundary 4
