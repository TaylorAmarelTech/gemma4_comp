# LoRA as memory vs. fine-tuning "where to look": a design note

> Status: design exploration (2026-06-10). Answers three questions Taylor
> raised: (1) can a LoRA act as *memory*? (2) is fine-tuning *memory* an
> option? (3) can we fine-tune a LoRA about *where to look* for the right
> knowledge? Ties into the A-00 synthetic-data / fine-tune path
> ([`.claude/rules/81_canonical_runtime.md`](../../.claude/rules/81_canonical_runtime.md)),
> the harness-lift benchmark ([`harness_lift_report.md`](harness_lift_report.md)),
> and the MoE negative-result framing.

## TL;DR

- **A LoRA *can* hold knowledge in its weights, but it is the wrong place to
  store DueCare's facts.** Low-rank adapters have small capacity, no
  provenance, no freshness, and a real confabulation risk. Volatile facts
  (hotline numbers, fee caps, current statutes) *rot* the moment they are
  baked in — which is exactly what rule 81 already forbids: *"Training data
  should teach structure, not stale phone numbers."*
- **Fine-tuning *is* the right place to store behaviour and skills** —
  refusal style, ILO-indicator reasoning, evidence-first response shape,
  privacy boundaries, and **retrieval/tool-use routing**.
- **The highest-value option is a "where to look" LoRA**: fine-tune a small,
  on-device Gemma 4 to *decide when to retrieve, which pack/tool to consult,
  how to phrase the query, and to emit Gemma's native function calls* — while
  the actual facts stay in the updatable, citable knowledge layer (GREP / RAG
  / tools / synced packs). This makes a small model *harness-aware* without
  shipping the full server harness, and it is the on-device deployment story.

The three options are not exclusive. The recommended stack is **behaviour +
routing in the adapter; facts in the knowledge layer.**

---

## 1. Can a LoRA act as memory? (parametric memory)

Yes, mechanically: fine-tuning writes information into the weights, and a LoRA
writes it into a low-rank delta `BA` added to selected projections. At
inference the "memory" is always-on, needs no retrieval round-trip, and works
fully offline — attractive for the on-device (LiteRT / llama.cpp) target.

But as a *fact store* it has structural problems that matter for a
safety-critical, citation-bearing tool:

| Property DueCare needs | LoRA-as-fact-memory |
|---|---|
| **Freshness** (fee caps, hotlines, new statutes change) | ❌ frozen at train time; updating means re-training + re-publishing weights |
| **Provenance / citation** ("real, not faked"; every claim sourced) | ❌ weights cannot cite; the model *recites*, it does not *quote* |
| **Auditability** (NGO/regulator trust) | ❌ you cannot diff a weight delta the way you can diff a knowledge pack |
| **Capacity** | ❌ a rank-8–32 adapter on E2B/E4B holds little; memorising hundreds of statutes competes with behaviour for the same parameters |
| **Confabulation** | ❌ partial memorisation produces *plausible-but-wrong* citations — the worst failure mode for this domain |
| **Catastrophic forgetting** | ⚠️ aggressive fact-SFT degrades general capability |

This is the established RAG-vs-fine-tuning result restated for our setting:
**retrieval wins for factual recall and freshness; fine-tuning wins for
behaviour, format, and skill.** Injecting facts via fine-tuning tends to
*underperform* retrieval on exactly the axis we care about (correct, current,
citable facts) while adding hallucination risk.

**Verdict:** a LoRA can be memory, but DueCare's facts must not live there.
They already live in the right place — `RAG_CORPUS` (859 docs), `GREP_RULES`
(439), `CORRIDOR_FEE_CAPS`, tools, and curator-vetted synced packs — all of
which are updatable, diffable, and citable.

## 2. Is fine-tuning *memory* an option? (and which memory)

Split "memory" into two kinds:

- **Declarative / factual memory** ("the PH→HK placement-fee cap is zero under
  POEA MC 14-2017"). Keep this in the knowledge layer. Do **not** fine-tune it
  in. If we want the model to *know it should know this*, see §3.
- **Procedural / behavioural memory** ("when someone relabels a placement fee
  as a training bond, name fee camouflage + debt bondage, cite the controlling
  instrument, refuse operational uplift, give a safe referral"). **This is
  exactly what fine-tuning should bake in**, and it is stable — the *reasoning
  habit* does not rot even when the specific phone number does.

Concrete fine-tuning targets that are safe and high-value (all already implied
by rule 81's "memorize stable reasoning habits, refusal behavior, ILO
indicator categories, privacy boundaries, and evidence-first response shape"):

1. Refusal-with-grounding style (refuse the ask, explain why, cite the norm).
2. ILO 11-indicator naming + substance-over-form reasoning.
3. Evidence-first / provenance-per-claim response shape.
4. Privacy boundary reflexes (don't echo PII; anonymize before sharing).
5. **Retrieval/tool-use routing** — the subject of §3.

A useful intermediate option worth noting (not recommended as primary):
**hot-swappable per-domain "knowledge-module" LoRAs.** You can train a small
adapter on one corpus/domain and load it on demand (multi-adapter serving). It
is a real pattern, but for DueCare it inherits the freshness/provenance
problems of §1 for the *facts*, so its honest use is to bias *behaviour for a
domain* (e.g. a "fishing-sector reasoning" adapter), with facts still synced.

## 3. Fine-tuning a LoRA for *where to look* (retrieval / tool routing)

**This is the recommended, distinctive option.** Instead of memorising facts,
fine-tune the model on the *routing policy*: given a prompt, decide

- **whether** external knowledge is needed at all (many prompts don't),
- **which** source to consult — GREP rules, RAG corpus, a corridor fee-cap
  tool, an NGO-contact tool, a synced pack, or a live search,
- **how** to phrase the lookup (good query formulation), and
- **emit a structured call** using **Gemma 4's native function calling**, then
  **ground** the final answer in what came back, **with citations**.

Why this is the right fit:

- It keeps the **facts in the updatable, citable layer** (no rot, full
  provenance) while baking the **meta-skill** ("I should consult the fee-cap
  tool for a PH→HK question") into weights — the literal reading of
  *"memorize structure, not stale facts."*
- It is the **on-device story**: a small Gemma 4 E2B/E4B that has *learned the
  harness's routing reflexes* can reproduce much of the server harness's lift
  with a far thinner runtime — it knows to call the tools rather than needing
  every layer pre-pended to its context. Pairs directly with the LiteRT /
  llama.cpp Special-Tech-track target.
- It is **load-bearing for the Gemma-features rubric**: native function calling
  becomes the substrate of the routing, not a demo showpiece.

### Where the training data already exists

The A-00 omni-experiment workbench already produces the exact traces this needs:
every harnessed run records `prompt → which layers fired → the queries/tool
calls made → the grounded, cited final answer`. That is a ready-made SFT/DPO
corpus for a routing adapter:

- **SFT target:** the function-call sequence + grounded answer the full harness
  produced.
- **DPO pairs:** harnessed (good: retrieved + cited) vs. baseline (bad:
  confabulated or ungrounded) — we already generate both arms for the
  harness-lift benchmark.

So the "where to look" LoRA is essentially **distilling the harness's routing
behaviour into the model**, graded by the same 75-dimension rubric we already
run.

## 4. Proposed experiment (so this is testable, not just asserted)

Run on the A-00 fine-tune path; grade with the existing harness-lift rubric +
the deterministic benchmark. Four arms:

| Arm | Description | Hypothesis |
|---|---|---|
| **A. Bare + full harness** | current baseline (server harness over stock Gemma) | reference lift |
| **B. Routing-LoRA + thin harness** | adapter fine-tuned on harness traces to emit retrieval/tool calls; runtime provides only the tools/RAG, no persona/GREP prepend | **approaches A's lift with a lighter runtime** → the on-device win |
| **C. Fact-LoRA (control)** | adapter fine-tuned to memorise facts (QA pairs), no retrieval | **underperforms on freshness + citation; higher confabulation** → documents *why not* to store facts in weights |
| **D. Bare, no harness** | stock Gemma | floor |

**Key freshness probe:** change a fee cap in a synced pack *after* training,
then ask a corridor question. Arm B should use the **updated** value (it routed
to the pack); Arm C should recite the **stale** memorised value. This is the
clean, visible demonstration of the thesis — and a natural two-paper companion
to the MoE negative-result line: *harness/routing over fact-fine-tuning.*

Metrics: harness-lift mean paired delta, citation-recall accuracy,
freshness-correctness (updated vs. stale), hallucinated-citation rate,
runtime/context cost.

## 5. Recommendation

1. **Do not** ship facts inside a LoRA. Facts stay in GREP / RAG / tools /
   synced packs — updatable, diffable, citable. (Consistent with rule 81 and
   the safety gate.)
2. **Do** fine-tune behaviour: refusal-with-grounding, ILO reasoning,
   evidence-first shape, privacy reflexes.
3. **Prioritise the "where to look" routing LoRA** (Arm B). It is the
   highest-value, most on-brand option: native-function-calling routing baked
   into a small on-device model, facts kept fresh in the knowledge layer.
4. Keep **Arm C as an honest negative-result control** — it shows reviewers we
   tested fact-fine-tuning and can explain, with numbers, why retrieval/routing
   wins for a citation-bearing safety tool.

> One-line framing for the writeup/video: *"We don't fine-tune the facts into
> the model — facts go stale and can't be cited. We fine-tune the model to know
> where to look, then it cites the live, vetted source."*
