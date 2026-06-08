# MoE fine-tuning fragility, routing-aware attacks, and why DueCare leans on the harness

> Compiled 2026-06-07. Citations independently web-verified (✅confirmed /
> ◐author-unverified / ⚠preprint / ❌not-found). Written to (a) ground a forum
> discussion on Gemma-4 fine-tuning fragility and (b) connect it to DueCare's
> harness-over-fine-tune thesis and the [learning-methods research](model_failure_study_methodology.md).

## 0. The correction that has to lead: Gemma 4 is NOT a classic MoE

Google's **Gemma 3n** (the "E2B / E4B effective-parameter" models this project calls
"Gemma 4") is **MatFormer (nested/elastic "Matryoshka" transformer) + Per-Layer
Embeddings (PLE) + selective parameter activation** — confirmed from Google's
official Gemma 3n docs and the MatFormer paper (Devvrit et al., *MatFormer: Nested
Transformer for Elastic Inference*, arXiv:2310.07707 ✅). **There is no per-token
gating network routing tokens to specialized expert FFNs.** E2B (~1.91B effective)
is a nested submodel *inside* E4B; the mechanism is nested-submodel selection +
offloaded PLE caching, not token-to-expert routing.

**Why this matters:** the entire MoE routing-attack literature below targets a
*token-to-expert gate*. Gemma 3n has no such gate, so those attacks apply to it
**by analogy, not directly.** Any claim that DeepSeek-style router-hijack transfers
to Gemma 4 as a demonstrated fact would be wrong. The *high-level* lesson ("safety
behaviour can concentrate in a sub-component that conditional computation can
bypass") may transfer conceptually; the specific exploits do not.

## 1. Are sparse / MoE models fragile to fine-tune? Yes — recipe-dependent

The fragility is real but comes from routing/sparsity/data-mismatch, not from MoE
capacity itself, and an MoE-aware recipe largely recovers it.

- **ST-MoE** (Zoph et al. 2022, arXiv:2202.08906 ✅) — the canonical stability paper:
  progress was "hindered by training instabilities and uncertain quality during
  fine-tuning"; bad sparse-model fine-tuning hyperparameters can erase most of the
  pretraining gains. Fixes: router z-loss + MoE-specific fine-tuning protocol.
- **Switch Transformer** (Fedus, Zoph, Shazeer 2021, arXiv:2101.03961 ✅) — sparse
  models overfit small fine-tuning sets (far more total params); remedy = low
  dropout at non-expert layers + **higher dropout inside expert FFNs**.
- **FLAN-MoE** (Sheng Shen et al. 2023, arXiv:2305.14705 ✅) — direct task
  fine-tuning makes MoE **underperform a FLOP-matched dense model**, but
  *instruction tuning* reverses it (FLAN-MoE-32B > FLAN-PaLM-62B at ⅓ FLOPs). The
  failure is recipe, not capacity.
- **ESFT** (DeepSeek, Wang et al., EMNLP 2024, arXiv:2407.01906 ✅) — task routing is
  concentrated; **tuning only the task-relevant experts (freeze the rest) matches or
  beats full-parameter fine-tuning** at much lower cost and less forgetting.
- **DenseMixer** (Yao et al., ICLR 2026, OpenReview `4HGIIekCx3` + GitHub
  `yaof20/DenseMixer` ◐ — **no arXiv ID**) — improves MoE post-training by giving the
  router a precise (straight-through) gradient instead of freezing it.

**Failure modes** (symptoms): router collapse / over-selection; overfitting on small
SFT; dense hyperparameters not transferring; catastrophic forgetting / domain
interference; gradient starvation of rarely-routed experts (which may hold useful
long-tail knowledge). **MoE-aware recipe:** freeze the router or use a much lower
router LR; LoRA/QLoRA on shared layers + selected experts; track expert utilization,
routing entropy, dropped-token rate, per-domain evals (not just loss); more
regularization (expert dropout); domain-balanced mixtures / replay; do a real sweep.

## 2. Can MoE models be "hacked" via routing-aware prompts? A real attack surface

Frame it as **a routing-specific attack surface**, not "anyone can hack MoEs with a
magic prompt." If safety behaviour is unevenly distributed across experts, an
adversary can try to steer inputs onto weaker routes. The literature is now explicit
(all verified real, Feb–May 2026):

- **Sparse Models, Sparse Safety: Unsafe Routes in MoE LLMs** (Jiang et al., CISPA,
  arXiv:2602.08621 ✅) — a Router Safety importance score; **masking 5 routers in
  DeepSeek-V2-Lite raises jailbreak ASR >4× (to ~0.79) on JailbreakBench.**
- **RouteHijack** (Xu et al., arXiv:2605.02946 ✅) — **input-only** adversarial suffix
  that suppresses safety experts; **69.3% avg ASR across 7 MoE LLMs**, transfers
  zero-shot to sibling variants and MoE-VLMs.
- **Misrouter** (Fei et al., arXiv:2605.04446 ✅) — input-only; optimizes on a
  white-box surrogate MoE, transfers to public API services.
- **GateBreaker** (Wu et al., arXiv:2512.21008 ✅) — **white-box**, training-free
  inference-time gate/expert attack; ASR 7.4%→64.9% across 8 MoE models. (Stronger
  attacker model than a normal API user — flag the access assumption.)
- **Large Language Lobotomy / L³** (te Lintelo, Wu, Picek, arXiv:2602.08741 ✅) and
  **SteerMoE** (Adobe, arXiv:2509.09660 ✅) — expert silencing / (de)activation drop
  safety up to −100% when combined with jailbreaks.

**The fine-tuning ↔ attack link** (the part that matters for the fragility thread):
- **SafeMoE / Defending MoE LLMs against Harmful Fine-Tuning via Safety Routing
  Alignment** (Kim et al., arXiv:2509.22745 ✅) — fine-tuning causes **routing drift**:
  harmful inputs no longer route through the safety-critical experts that handled
  them before. Defense = preserve the safety-aligned router. Reduces OLMoE
  harmfulness 62.0→5.0.
- **RASA: Routing-Aware Safety Alignment** (Liang et al., arXiv:2602.04448 ✅) —
  fine-tune only safety-critical experts under fixed routing, then re-align the
  router.

So: uneven SFT impact on routers/experts (the observed fragility) can create
**pockets that are easier to trigger** — the safety drift and the attack surface are
two views of the same routing non-uniformity. **Caveat for Gemma:** all of the above
assume a token-to-expert router. Gemma 3n's MatFormer has none, so treat
routing-hijack on Gemma 4 as an **open analogy**, not a demonstrated result.

## 3. Why this is a DueCare argument, not a detour

The fragility + routing-drift findings line up exactly with the broader
alignment-limitation evidence (see [methodology](model_failure_study_methodology.md)):
**shallow safety alignment** (Qi et al. 2024, arXiv:2406.05946 ✅), **benign
fine-tuning erodes safety** (Qi et al. 2023, arXiv:2310.03693 ✅), **specialized
knowledge is long-tail** (Kandpal et al. 2023, arXiv:2211.08411 ✅), and **retrieval
grounds** (Lewis et al. 2020, RAG, arXiv:2005.11401 ✅).

The synthesis — and DueCare's design rationale:

1. **Bare SFT on a sparse/nested model oversteers.** It moves a thin, behavioural
   layer unevenly across submodels/experts → gains on the training distribution,
   brittle regressions adjacent to it, and (for true MoE) safety routing drift.
2. **So fine-tune narrowly, for structure not facts.** Memorize stable *habits* —
   refusal style, ILO-indicator reasoning, evidence-first response shape — sparingly
   (ESFT-style selective tuning is the literature's answer); do NOT cram volatile
   facts in, which benign fine-tuning can destabilize anyway.
3. **Put the heavy lifting in the harness, outside the weights.** Context
   construction + RAG + GREP + recursive validation/grading is exactly the
   "context > fine-tuning" pattern the thread author observed. Critically, the
   **DueCare harness sits OUTSIDE the model**, so it does not depend on the model's
   internal routing staying safe — it is **robust to routing/SFT drift by
   construction.** A routing-aware jailbreak that steers the model onto a weaker
   path still has to pass the deterministic GREP/RAG/grading layer.

That is the load-bearing point: **a model whose safety lives in fragile internal
routing is an argument FOR a deterministic outer safety harness** — DueCare's
architecture — not against using Gemma 4. (The step 1→3 division of labour is a
design choice consistent with the evidence, not itself a single published result —
flag as synthesis.)

## 4. Bottom line

- Gemma 4 = MatFormer + PLE, **not classic MoE**; the routing-attack papers apply by
  analogy only.
- Sparse/MoE/nested models are **higher-variance to fine-tune**, not unusable; the
  fix is an architecture-aware recipe (selective tuning, frozen/low-LR router,
  regularization, routing-aware evals).
- MoE routing **is** a real, now-documented attack surface (and harmful fine-tuning
  causes safety routing drift) — but most strong attacks assume white-box/surrogate
  access; state the access assumptions honestly.
- All of this strengthens the **harness-over-heavy-fine-tune** thesis: keep safety in
  a deterministic layer outside the weights, fine-tune narrowly for habits, retrieve
  the rest.
