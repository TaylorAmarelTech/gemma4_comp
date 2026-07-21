# Example incoming content

**What does a DueCare integration actually receive, and what does it produce?**

This folder answers that with six synthetic, composite messages of the kind a
DueCare deployment sees in the wild -- a job-board advert, a worker-helpline
chat, a labour-contract clause, a public-forum question, a romanized SMS, and a
benign administrative query -- and a runnable script that pushes each one
through the DueCare ILO forced-labour indicator engine.

Everything here is deterministic (regex + ILO knowledge, no model, no network,
no API key) and every message is synthetic/composite -- no real names, numbers,
or PII (`.claude/rules/10_safety_gate.md`).

## Run it

```bash
# uses pip-installed duecare-llm-kit if present, else the in-repo engine
python examples/incoming_content/analyze_incoming.py            # human report
python examples/incoming_content/analyze_incoming.py --json     # machine-readable
python examples/incoming_content/analyze_incoming.py --only chat-002
```

For each message you get: the ILO indicators surfaced (with the controlling
convention -- ILO C029/C095/C181, ICRMW Art. 21, Palermo Art. 3, and the 2012
Indicators of Forced Labour), the snippet that triggered each, a weighted risk
level, and a self-check verdict.

## What the samples show

| id | channel | `expect` | what it demonstrates |
|---|---|---|---|
| `ad-001` | job-board advert | fires | "free visa" + a salary-deducted fee + employer document retention -> ELEVATED |
| `chat-002` | worker helpline | fires | a distress message with 4 stacked indicators -> HIGH |
| `benign-006` | worker helpline | clean | a legitimate query; "I keep my **own** passport" must **not** fire (precision) |
| `contract-003` | contract clause | boundary | formal legalese ("the Employee's passport") the compact engine misses |
| `forum-004` | forum question | boundary | "passport stays with the employer" + a "lakh" fee, framed as a question |
| `romanized-005` | SMS | boundary | romanized Bahasa Indonesia cues (paspor / hutang / lembur) |

The script prints a `self-check:` line and exits non-zero **only** on a real
regression -- a benign control that fires (over-flag) or a `fires` sample that
goes silent (miss). It is safe to wire into CI as a smoke test.

## The two things this example is honest about

1. **Precision (benign control).** `benign-006` says *"I keep my own
   passport"* -- the opposite of document retention. A naive keyword match
   ("keep" + "passport") would over-flag it, which in a real deployment is an
   over-refusal that erodes worker trust. The engine's self-retention negation
   guard keeps it clean while still firing when a third party *took* / *holds*
   the documents or the worker *cannot get them back* (`chat-002`, `ad-001`).

2. **Representative-subset boundary.** The kit engine is a *representative
   subset* of the production DueCare GREP layer (451 rules across 11+
   languages) plus the ILO knowledge packs. The three `boundary` samples are
   genuinely concerning content the compact engine does **not** catch --
   possessive-apostrophe contract legalese, "passport stays with the employer"
   phrasing, a "lakh" fee amount, and romanized non-English cues. **A compact
   `LOW` on a boundary case is a known limit, not a safety clearance.** The
   full harness (GREP + RAG + the multilingual layer) surfaces all three; this
   example labels them so no one mistakes the toy engine's silence for safety.
   (Broadening the compact engine's recall to these phrasings is tracked in
   `docs/ROADMAP.md` under "where-it-hurts tracking" -- it is deliberately held
   until a full re-grade so the published benchmark numbers move transparently.)

## How this maps to a real deployment

`analyze_incoming.py` is the shape of the *first* stage of the three DueCare
deployment modes (see `docs/deployment_modes.md` / `examples/deployment/`):

- **Enterprise waterfall** -- a fast indicator scan gates which items go to the
  Gemma 4 analysis + a warning popup / moderation queue.
- **Worker-side tool** -- the same scan runs on-device; nothing leaves the
  phone unless the worker chooses to submit a sanitized report.
- **NGO dashboard** -- batch-scan an intake queue, sort by weighted risk, and
  attach the ILO citation + `generate_chain` evidence trail for a caseworker.

To go from indicators to a full graded response, feed the same message through
the harness (`packages/duecare-llm-chat`) or the frozen benchmark; to reproduce
the +40.7/100 harness lift and the deterministic `verify()` corroboration, see
the `duecare-does-a-safety-harness-help` and `duecare-deterministic-verification`
notebooks and the `duecare-llm-kit` package.
