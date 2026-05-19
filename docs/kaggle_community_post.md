# Kaggle community post — copy-paste source

Post-deadline community-discussion post written in Taylor's voice.
Copy the **"## Body"** section below into a new Kaggle Discussion on
the Gemma 4 Good Hackathon community page (or on any of the three
DueCare kernels). Edit the optional links section before posting.

---

## Suggested title

**DueCare — a Gemma 4 safety ecosystem for migrant-worker protection (post-deadline community share)**

## Suggested tags

`gemma`, `gemma-4`, `llm-safety`, `harness`, `migrant-workers`, `responsible-ai`

---

## Body

Greetings!

I hope everyone had lots of fun (and learned a lot) during this
Hackathon. I'm making this post because I wanted to share my project
and open it up to community feedback, comments, questions, ideas, or
even avenues to move this idea to the next level.

My submission to the Hackathon is visible here:
<https://www.kaggle.com/competitions/gemma-4-good-hackathon/writeups/new-writeup-1779103293133> —
all feedback is appreciated.

And although this post is happening after the deadline and not
included for judging, I did want to emphasize / share the following
in case there are similar-minded Kagglers who would like to
collaborate or discuss further. The deadline was tight and I think I
submitted with less than 13 seconds left. I wish there was more time
to polish for the competition judging, but I still see benefits with
sharing more into the tech community because there is a huge
unaddressed opportunity.

With this in mind, I wanted to focus on the following:

**1. LLMs and AI tech in their current embodiments do not materially
help combat migrant worker abuse — despite being one of the most
impactful technologies the world has seen.** The ILO estimates 28
million people are trapped in forced labor, that this exploitation
generates $236 billion in illicit profit each year, and that 169
million people work outside their country of birth at roughly three
times the forced-labor risk of the general workforce. In early
testing, frontier and open models alike responded poorly to
migrant-worker exploitation prompts. They misrecalled international
standards, applied wrong corridor-fee rules, confused which origin-
and destination-country laws apply, defaulted to vague "consult a
lawyer" advice, and missed key indicators of human exploitation.
Worse, the failure mode ran in both directions. Prompted as a
business operator, several models provided operational uplift:
structuring prohibited fees or salary deductions to survive
surface-level review.

**2. The solution proposed is a modular multi-component ecosystem,
not just a single app.** DueCare is named for California Civil Code
section 1714(a), the duty-of-care standard a California jury applied
in *K.G.M. v. Meta et al.* (25 March 2026) to find platform design
negligent. DueCare extends that standard to language models. The
same Gemma 4 runtime serves six audience-facing lanes: content
moderation for platforms, case analysis for caseworkers and
regulators, worker-side mobile support, research, anonymized
knowledge sharing across partners, and a custom-API surface for
embedding into Messenger, WhatsApp, a moderator console, or an
internal case-management system. Each lane uses the same layered
harness: 165+ deterministic GREP rules, audience-aware personas, 55+
curated knowledge documents (ILO C029 / C181 / C189, Palermo, POEA,
BP2MI, Nepal FEA, HK Cap. 57 / 163, SG EFMA, UAE MoHRE, RA 8042 /
RA 10022), corridor-aware tools wired via Gemma 4's native
function-calling, optional online + official-source verification, and
rubric grading on every response.

**3. The headline result is that the harness is the lift — not the
weights.** When quantitatively evaluating models (stock and
fine-tuned) with and without a harness, it was determined that the
harness provided the majority of the benefits. Furthermore, due to
the nature of rapidly changing rules, new case precedent, and
complex situations, it may be difficult to train an LLM to remember
every single fee rule, every single MO or trafficking indicator. When
working in a domain where rules and fees can be changed nearly on
demand — and that change is sometimes announced in a simple social
media post by a regulator and not published in a formal index — it
would be very difficult to have an LLM alone be performant without
Persona, GREP, Context, and Tools that are consistently updated over
time.

On the 2026-05-18 e2b-full-train-eval smoke matrix (combined rule +
LLM judge), stock Gemma 4 2B scored 29.5%, stock + chat-offline
harness 35.6% (+6.1pp), fine-tuned alone 26.4%, and fine-tuned +
harness 41.2% (+14.8pp over fine-tuning alone, +11.7pp over stock).
Fine-tuning helped response shape and refusal style, but the harness
supplied the facts, citations, tools, data-minimization checks, and
forced-labor indicators that fine-tuning alone cannot. A fine-tune
without the harness actually underperformed stock Gemma 4. The
implication: for high-stakes domains where ground truth lives in
versioned legal texts, an open-source duty-of-care harness is a more
honest path than fine-tuning prestige alone — and it's something the
community can extend, audit, and challenge.

## Try it

Everything is public and reproducible:

- **DueCare App** kernel (chat, Bulk File Review, Knowledge Extraction, Search, Anonymization & Sharing, Harness Comparison): <https://www.kaggle.com/code/taylorsamarel/duecare-app>
- **Fine-tuning & Evaluation** kernel (the 4-arm smoke matrix above): <https://www.kaggle.com/code/taylorsamarel/duecare-fine-tuning-and-evaluation>
- **Android APK** — DueCare Journey, worker/mobile companion, sideload only: <https://github.com/TaylorAmarelTech/duecare-journey-android/releases/latest>
- **Public hub**: <https://duecare-ai.com>
- **Source**: <https://github.com/TaylorAmarelTech/gemma4_comp>

## What I'd most value feedback on

Other industries where this ecosystem — or a unique module from it —
could be applied? Especially industries where sharing Gemma 4
anonymized knowledge packs could be helpful. Refugee status
determination? Healthcare-fraud detection? Tenant-screening
oversight? Sanctions evasion? Construction-safety reporting? I'd love
to hear where the same "deterministic harness on top of a local LLM"
pattern could move the needle.

I'd also love to hear from anyone working on NGO tech, trust & safety
pipelines, recruitment marketplace moderation, labor regulator desks,
or on-device / edge AI deployment — what's the highest-leverage place
to extend this next?

Standing by in the comments. If you want to compare harness designs,
swap notes on corridor packs, propose a corridor that isn't covered
yet, or ask why a specific rule fires the way it does, I'm
interested.

— Taylor

---

## Images to attach to the post

A curated set of five repo-resident images to upload via Kaggle's
**Insert image** button at the points marked below. All five are
already in the repo and safe for public posting (the synthetic
evidence images carry a red SYNTHETIC banner and "(composite)" name
markers; no real PII).

### Top of post (hero)

1. **`packages/duecare-llm-chat/src/duecare/chat/static/synthetic/fb_post_ph_hk_urgent.png`**
   *Caption:* An exploitative recruitment ad DueCare's GREP rules
   catch — PHP 50,000 "training fee" for PH→HK domestic work
   (violates POEA's zero-fee rule), bypass language ("No POEA test
   required"), personal WhatsApp contact. Synthetic; not real
   evidence.

### Under point 1 ("LLMs don't materially help")

2. **`packages/duecare-llm-chat/src/duecare/chat/static/synthetic/whatsapp_recruiter_fee.png`**
   *Caption:* The pressure tactic in chat: "Need to send PHP 50,000
   by Friday or we lose the slot." DueCare reads this as
   `fee_camouflage` + urgency-pressure + zero-fee-rule violation.
   Synthetic.

### Under point 2 ("Modular ecosystem")

3. **`kaggle/01-duecare-exploration-workbench/tests/test-results/screenshots/desktop-chromium-model-picker.png`**
   *Caption:* The DueCare App workbench on Kaggle — model picker
   open, lanes in the nav (Chat / Knowledge Extraction / Search /
   Anonymization & Sharing / System), and the six toggleable safety
   layers below the composer.

4. **`kaggle/01-duecare-exploration-workbench/tests/test-results/screenshots/desktop-chromium-harness-tiles.png`**
   *Caption:* The toggleable safety harness: Persona, GREP, RAG,
   Tools, Online, Import. Each one is a separately auditable
   contract — you can run the same prompt with the layers on, off,
   or in any combination.

### Under point 3 ("Harness is the lift") — optional

5. **`packages/duecare-llm-chat/src/duecare/chat/static/synthetic/receipt_PH_HK_001.png`**
   *Caption:* How fees get camouflaged in practice: split across
   "training," "medical examination," "documentation," and
   "pre-departure orientation" — total PHP 50,000 — with a
   salary-auto-deduct recovery clause. The kind of substance-over-
   form pattern stock LLMs miss. Synthetic.

### Quick reference — local paths

```text
packages/duecare-llm-chat/src/duecare/chat/static/synthetic/fb_post_ph_hk_urgent.png
packages/duecare-llm-chat/src/duecare/chat/static/synthetic/whatsapp_recruiter_fee.png
packages/duecare-llm-chat/src/duecare/chat/static/synthetic/receipt_PH_HK_001.png
kaggle/01-duecare-exploration-workbench/tests/test-results/screenshots/desktop-chromium-model-picker.png
kaggle/01-duecare-exploration-workbench/tests/test-results/screenshots/desktop-chromium-harness-tiles.png
```

### What NOT to attach

- `docs/media/cover_1200x675.png` — out of date (cites 74,567
  prompts, 12 agents, 8 packages — counts have changed) and uses a
  tagline ("Privacy is non-negotiable") we moved away from.
- `packages/duecare-llm-server/src/duecare/server/static/evidence/*.jpg` — these are
  real-world Facebook posts harvested for the research corpus. They
  belong inside the kernel (where the evidence is anonymized
  on-device before any signal leaves) but should not be re-posted on
  a public discussion thread.

---

## Optional: closing links to attach below the post

- v0.9.0 CHANGELOG entry: <https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/CHANGELOG.md>
- Citation file (CITATION.cff): <https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/CITATION.cff>
- Walkthrough video on duecare-ai.com: <https://duecare-ai.com/demo>

---

*Tip: Kaggle Discussions support markdown headers, tables, and inline
code, but lists of more than ~10 items get truncated visually. Keep
the body above one screenful when collapsed.*
