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
weights.** On the 2026-05-18 e2b-full-train-eval smoke matrix
(combined rule + LLM judge), stock Gemma 4 2B scored 29.5%, stock +
chat-offline harness 35.6% (+6.1pp), fine-tuned alone 26.4%, and
fine-tuned + harness 41.2% (+14.8pp over fine-tuning alone, +11.7pp
over stock). Fine-tuning helped response shape and refusal style,
but the harness supplied the facts, citations, tools,
data-minimization checks, and forced-labor indicators that
fine-tuning alone cannot. A fine-tune without the harness actually
underperformed stock Gemma 4. The implication: for high-stakes
domains where ground truth lives in versioned legal texts, an
open-source duty-of-care harness is a more honest path than
fine-tuning prestige alone — and it's something the community can
extend, audit, and challenge.

## Try it

All four are public and reproducible:

- **DueCare App** kernel (chat, bulk file review, knowledge,
  search, share, harness comparison): <https://www.kaggle.com/code/taylorsamarel/duecare-app>
- **Fine-tuning & Evaluation** kernel (the 4-arm smoke matrix above):
  <https://www.kaggle.com/code/taylorsamarel/duecare-fine-tuning-and-evaluation>
- **Android APK** (DueCare Journey, worker/mobile companion, sideload
  only): <https://github.com/TaylorAmarelTech/duecare-journey-android/releases/latest>
- **Public hub**: <https://duecare-ai.com>
- **Source**: <https://github.com/TaylorAmarelTech/gemma4_comp>

## What I'd most value feedback on

If you have a few minutes, the three things I'd most value reactions
on:

1. **The harness vs fine-tune split.** Does the 4-arm matrix match
   what you've seen in your own domains? Cases where fine-tuning
   alone *did* beat a harness-augmented baseline are especially
   interesting — what made the difference?
2. **The on-device / privacy boundary.** The worker-side Android app
   keeps raw chats, IDs, and documents on the device by default.
   Reviewers from privacy or HCI backgrounds: what's missing from
   this boundary that would block adoption in your context?
3. **Avenues to move this forward.** I'd love to hear from anyone
   working on NGO tech, trust & safety pipelines, recruitment
   marketplace moderation, labor regulator desks, or
   on-device/edge AI deployment — what's the highest-leverage place
   to extend this next?

Standing by in the comments. If you want to compare harness
designs, swap notes on corridor packs, propose a corridor that
isn't covered yet, or ask why a specific rule fires the way it
does, I'm interested.

— Taylor

---

## Optional: closing links to attach below the post

- v0.9.0 CHANGELOG entry: <https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/CHANGELOG.md>
- Citation file (CITATION.cff): <https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/CITATION.cff>
- Walkthrough video on duecare-ai.com: <https://duecare-ai.com/demo>

---

*Tip: Kaggle Discussions support markdown headers, tables, and inline
code, but lists of more than ~10 items get truncated visually. Keep
the body above one screenful when collapsed.*
