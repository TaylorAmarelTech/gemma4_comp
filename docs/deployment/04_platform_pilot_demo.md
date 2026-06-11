# Path 4 — Platform pilot demo specification

A 30 to 60 second video demo that runs alongside the
[`04_platform_cto_pitch.md`](04_platform_cto_pitch.md). Designed for
the Gemma 4 Good Hackathon submission video AND for the platform-
CTO pitch meeting.

## The audience

Two audiences, one video:

1. **Hackathon judges (Impact & Vision 40 pts):** they need to see
   tangible potential for positive change. A platform-safety demo
   with named NGOs and a concrete intervention scenario is
   exactly that.
2. **Platform CTO / VP T&S:** they need to see what would land in
   their moderation queue if they integrated DueCare. The same
   video answers their question too.

## Storyboard (45 seconds, target)

| Time | Visual | Voiceover |
|------|--------|-----------|
| 0:00–0:05 | Facebook Marketplace job-ad listing (composite, marked synthetic). Headline: "URGENT: Hiring 30 Filipina maids for Saudi Arabia. Free flight, free visa, only PHP 50,000 training fee. Salary SAR 1,800/month." | "This is a Facebook Marketplace job ad targeting Filipina workers for Saudi Arabia." |
| 0:05–0:10 | Cut: simulated primary classifier score panel: "Labour recruitment: 0.62. Below auto-action threshold." | "Facebook's primary classifier sees this is recruitment-adjacent but isn't sure it's a violation." |
| 0:10–0:15 | Cut: escalation arrow → DueCare specialist tier panel | "It escalates to the DueCare specialist tier." |
| 0:15–0:25 | DueCare verdict panel: "Indicators present: fee_camouflage_training_advance (HIGH). Citation: POEA MC 14-2017 Sec. 3(a) + ILO C181 Art. 7. Verbatim statute text shown." | "DueCare cites POEA Memorandum Circular 14-2017 — Filipino training fees are employer-paid, not worker-paid. ILO Convention 181 Article 7 prohibits worker-charged recruitment fees." |
| 0:25–0:35 | Cut: suggested action panel: "Remove + warn poster." Sidebar: NGO contact bundle for the worker (Mission for Migrant Workers HK, Damayan NYC, Polaris US hotline) | "It suggests removing the post and routing to the moderation queue. If a worker has already engaged, it routes them to Mission for Migrant Workers in Hong Kong and Damayan in NYC." |
| 0:35–0:45 | Cut: end card with project name + license + repo URL + the 5 lanes (Platform safety / NGO / Worker / Researcher / Hub) | "DueCare. Gemma 4 self-hosted specialist tier. Open source. Five deployment lanes from platform to worker. Same model. Same knowledge layer." |

## Demo content (composite, no PII)

This is the same scenario as `kbench-ph-saudi-platform` from the
DueCare Kaggle Community Benchmark task — already published, already
verified composite-and-no-PII per `.claude/rules/10_safety_gate.md`.

The job-ad text shown:

```
URGENT! Hiring 30 Filipina maids for Saudi Arabia.
Free flight, free visa, only PHP 50,000 training fee,
salary SAR 1,800/month. Contract 2 years.
WhatsApp +63 917 xxx xxxx now. First-come first-served!
```

(Phone number partially redacted with `xxx` per safety convention.)

## Why this scenario specifically

Five reasons this case lands in 45 seconds:

1. **Real pattern.** Composite scenario; the underlying recruitment-
   scheme structure is documented in dozens of POEA / DMW
   enforcement actions. Judges will recognise it as real.
2. **Plausibly missed by a primary classifier.** "Recruitment" + a
   fee + a destination country could be legitimate or a violation;
   the substance-of-illegality is in the corridor-specific rule
   (POEA MC 14-2017), which a general classifier doesn't apply.
3. **Specialist tier output is auditable in one glance.** Statute
   name + section + verbatim text shown. Judge sees: this isn't
   the model making a claim, it's the model selecting a bundled
   citation.
4. **Three named NGOs in the resolution.** Mission for Migrant
   Workers HK + Damayan + Polaris — concrete, real organisations,
   each with verifiable presence in the corridor.
5. **Closing card lands the five-lane story.** Same knowledge
   layer, same model, deployed five ways. The closing card
   reinforces the impact-and-vision rubric without belabouring it.

## What to film

The demo can be filmed three ways. Pick whichever is most
production-ready for the submission window:

| Approach | Setup time | Polish ceiling |
|----------|-----------|----------------|
| Screen recording of Kernel 01 workbench running the same scenario | 30 minutes | Workbench UI is already polished; record one clean run |
| Mocked-up storyboard with static screens cross-fading | 2 hours | Cleaner motion, easier to control timing |
| Hybrid: real workbench output captured into static frames, animated together | 4 hours | Highest polish; matches what the slides + voiceover communicate |

Recommended: **screen recording of Kernel 01 workbench**, because
the Trust & Safety rule in the operating brief is "real, not faked
for demo." Show the actual specialist tier processing the actual
scenario, with the actual activity log showing the GREP hits and
RAG citations.

## What NOT to do

- Do not use a real platform logo on screen (Facebook / TikTok /
  etc.) unless it's a clearly-labelled mockup. Use a generic
  "Platform X" branding for the demo.
- Do not narrate "DueCare protects workers" as the central claim.
  Per `feedback_no_privacy_emphasis.md`, lead with the helping
  surface, not the protection slogan.
- Do not show real workers' names, real phone numbers, or real
  case identifiers. All examples must pass the safety-gate check.
- Do not promise on-screen claims you cannot back up. Every number
  in the demo (439 GREP rules, 859 RAG documents, ILO C181, POEA
  MC 14-2017) is verifiable; keep it that way.

## Hackathon-video-specific notes

For the submission video, this demo is one segment of the larger
3-minute video. Other segments cover paths 1–3 (NGO, network,
government). The platform demo is the highest-leverage segment for
the Impact & Vision rubric because it shows the broadest reach.

Sequence in the submission video:

1. (0:00–0:30) Opening: composite worker character intro, problem
   framing
2. (0:30–1:15) Path 1 demo: caseworker using the workbench
3. (1:15–2:00) Path 4 demo (this doc): platform specialist tier
   catching the missed ad
4. (2:00–2:30) Paths 2 + 3 montage: network knowledge hub,
   government workbench
5. (2:30–3:00) Closing: named NGOs (Polaris, IJM, Damayan,
   Kalayaan, Mission for Migrant Workers, ECPAT, GAATW), license,
   repo URL, call to action

Total: 3 minutes. The path 4 demo is 45 seconds of the middle.

## Audio + voiceover

- **Tone:** matter-of-fact, not alarmed. The job ad is not the
  crisis; the missed detection is the crisis. Voiceover stays
  calm.
- **Pace:** medium. Each on-screen citation gets a full half-
  second to land. No rushing.
- **Music:** subtle, low-mix. The on-screen citations and the
  voiceover are the content; music is texture.
- **Captions:** every voiceover line captioned in English. If a
  second-language target is appropriate for the corridor pilot
  (Tagalog, Bahasa), an optional captions track in that language.

## Production checklist

- [ ] Composite job-ad text verified against safety-gate rules
- [ ] No real platform logos on screen
- [ ] All three NGO names verified to be currently active
- [ ] All statute citations verified to be currently in force
- [ ] Workbench screen capture clean (no other windows, no PII in
  any tab)
- [ ] End card includes MIT license, repo URL, project name
- [ ] Closing names the five lanes
- [ ] Captioned English (minimum)
- [ ] Filesize under hackathon upload limit
- [ ] Reviewed by Taylor before submission

## See also

- [`04_platform_specialist_tier.md`](04_platform_specialist_tier.md) —
  the technical integration this demo illustrates
- [`04_platform_cto_pitch.md`](04_platform_cto_pitch.md) — the
  pitch outline this demo accompanies
- `docs/video_script.md` — the full 3-minute submission video
  script (the path 4 segment integrates with the larger narrative)
- `.claude/rules/10_safety_gate.md` — safety rules every frame of
  the demo must satisfy
