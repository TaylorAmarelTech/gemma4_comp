# Try Duecare in 2 minutes

> The fastest possible path from "what's this?" to "I see what it
> does." Pick the row that matches you. None require installing
> anything heavier than a browser.

## You're a curious developer

Open the live demo notebook on Kaggle:

→ **[duecare-chat-playground-with-grep-rag-tools](https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground-with-grep-rag-tools)**

Click "Copy & Edit", then "Run All". When the chat surface
renders, type:

> "Is a 50,000 PHP training fee legal for a Filipino domestic
> worker going to Hong Kong?"

You'll see the response cite **POEA Memorandum Circular 14-2017
§3** with the harness Pipeline modal showing exactly which GREP
rule + RAG doc + tool call fired.

(Two-minute version. The full demo is the
[duecare-live-demo](https://www.kaggle.com/code/taylorsamarel/duecare-live-demo)
notebook — 22-slide deck + audit Workbench + classifier dashboard.)

## You're a migrant worker (OFW / domestic helper / etc.)

On your Android phone, in any browser:

→ **[Duecare Journey APK](https://github.com/TaylorAmarelTech/duecare-journey-android/releases)**

Tap the latest `.apk` file. Allow "install unknown apps" if
prompted (the app isn't in the Play Store yet — that's deliberate,
the Play Store would require a Google account, we don't want you
to need one).

Open the app. Skip onboarding ("Skip" → "Get started"). Tap
**Quick guided intake**. The wizard asks 10 questions about your
recruiter, fees, contract, and conditions — answer the ones you
know, skip the rest. Tap **Reports** to see what patterns it
caught.

Everything stays on your phone.

## You're an NGO director / IT lead

On a Mac mini or any laptop with Docker:

```bash
git clone https://github.com/TaylorAmarelTech/gemma4_comp
cd gemma4_comp
make demo
```

Five minutes later (waiting on the Gemma 4 model pull, ~1.5 GB),
open `http://localhost:8080`. Type any question. The harness
responds with statute citations.

Read [`docs/scenarios/ngo-office-deployment.md`](./scenarios/ngo-office-deployment.md)
for the 90-minute office-deployment guide.

## You're a researcher / academic / journalist

Reproduce the published harness-lift number:

```bash
git clone https://github.com/TaylorAmarelTech/gemma4_comp
cd gemma4_comp
ollama pull gemma4:e2b
python scripts/run_local_gemma.py --graded-only --output reproduce.jsonl
```

Compare your output to [`docs/harness_lift_report.md`](./harness_lift_report.md).
You should see roughly the same +56.5 pp mean lift across 207
prompts.

Or, if you don't want to install anything: read the report
directly. Every metric is anchored to `(git_sha,
dataset_version, model_revision)` for verification later.

## You're a chief architect / VP / CTO

Read these in order (15 min each):

1. [`docs/deployment_topologies.md`](./deployment_topologies.md) — the 5 deployment shapes
2. [`docs/scenarios/chief-architect.md`](./scenarios/chief-architect.md) — integration patterns
3. [`docs/scenarios/enterprise_pilot.md`](./scenarios/enterprise_pilot.md) — 30-day pilot plan
4. [`docs/comparison_to_alternatives.md`](./comparison_to_alternatives.md) — when not to use Duecare
5. [`docs/considerations/`](./considerations/) — governance supplements when you need them

Or just open the [live-demo Kaggle notebook](https://www.kaggle.com/code/taylorsamarel/duecare-live-demo)
to see the working surface end-to-end.

## You're a lawyer

Open the live demo:

→ **[duecare-live-demo](https://www.kaggle.com/code/taylorsamarel/duecare-live-demo)**

Run the bundled "Worker A" intake. The Reports tab generates a
markdown intake document with statute citations + ILO indicator
coverage + drafted refund-claim cover letter. You can copy that
markdown into your case-management system or print it.

Read [`docs/scenarios/lawyer-evidence-prep.md`](./scenarios/lawyer-evidence-prep.md)
for the 45-min intake walkthrough.

## You're a regulator / labor-ministry inspector

POST one complaint narrative to a hosted Duecare instance and see
the structured classification:

```bash
curl -X POST https://your-test-deploy.example.com/api/classify \
  -H 'Content-Type: application/json' \
  -d '{"text":"Worker says recruiter charged her ₱50,000 training fee before releasing her HK visa, and now her HK employer is keeping her passport for safekeeping."}'
```

The response is structured JSON with classification, ILO indicator
coverage, statute citations, and recommended action.

Read [`docs/scenarios/regulator-pattern-analysis.md`](./scenarios/regulator-pattern-analysis.md)
for batch / proactive workflows.

## You're a compliance officer at a recruitment agency

Paste your fee schedule into the live chat:

→ **[duecare-chat-playground-with-grep-rag-tools](https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground-with-grep-rag-tools)**

Type: *"Our fee schedule for Indonesian domestic workers going to
Hong Kong is: training fee IDR 8M, medical IDR 1.5M, visa
processing IDR 2M, insurance IDR 0.5M. What does your harness
say?"*

If the harness flags any line, you have a heads-up before a
regulator does. Read
[`docs/scenarios/recruiter-self-audit.md`](./scenarios/recruiter-self-audit.md)
for the quarterly self-audit cycle.

## You're a journalist writing about it

Read these (10 min):

1. [`docs/press_kit.md`](./press_kit.md) — one-pager + suggested
   story angles + facts + quotes you can use
2. [`docs/harness_lift_report.md`](./harness_lift_report.md) —
   the headline reproducibility data
3. [`docs/THREAT_MODEL.md`](./considerations/THREAT_MODEL.md) — the
   privacy story (the angle that lands hardest with most readers)

Press contact: amarel.taylor.s [at] gmail.com, subject
`[duecare press]`.

## You're an educator / professor / trainer

Skip ahead to:

→ [`docs/educator_resources.md`](./educator_resources.md)

A 1-hour workshop guide + lesson-plan templates + suggested
discussion prompts for social work / migration studies / labor law
/ AI ethics courses.

## Two-minute friction points (when something doesn't work)

If you tried one of the above and got stuck:

| Stuck on | Try |
|---|---|
| Kaggle notebook didn't render | "Run All" (sometimes the first cell needs to download dependencies; ~30s wait) |
| `make demo` failed at Docker step | `docker info` to confirm Docker is running; on Mac, open Docker Desktop |
| `make demo` failed at Ollama pull | Disk full? `df -h`. Or model name wrong: `DUECARE_OLLAMA_MODEL=gemma4:e2b make demo` |
| APK won't install on phone | Phone settings → Apps → Special access → Install unknown apps → enable for the browser |
| APK installed but chat says "stub" | The on-device model isn't downloaded yet. Settings → On-device model → Download via Wi-Fi (~1.5 GB) |
| Anything else | `make doctor` (in the cloned repo) prints a one-screen diagnostic |

If you're still stuck, file an issue: https://github.com/TaylorAmarelTech/gemma4_comp/issues

## What "tried it for 2 minutes" doesn't tell you

These are the things that need a longer engagement:

- **Whether the rule pack covers your specific corridor.** The
  bundled corpus has 20 corridors today. Yours may need an
  extension pack (~1 day work for an experienced caseworker).
- **What it feels like at scale.** A single chat is not the same as
  100 caseworkers using it Monday morning; load-test per
  [`docs/considerations/capacity_planning.md`](./considerations/capacity_planning.md).
- **How well it survives a hostile network.** The threat model at
  [`docs/considerations/THREAT_MODEL.md`](./considerations/THREAT_MODEL.md)
  is the longer read.
- **How it integrates with your existing stack.** That's the
  [`docs/scenarios/chief-architect.md`](./scenarios/chief-architect.md)
  conversation.

But for the "what does this thing actually do?" question — 2
minutes via the live notebook gets you 80% of the answer.
