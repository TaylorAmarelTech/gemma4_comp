# Codex for Open Source - application answers (DueCare)

Plain-text answers for the OpenAI Codex for Open Source form. Everything here is true and checkable in the repo. The four capped fields are all under 500 characters.

## First name

Taylor

## Last name

Amarel

## Email

amarel.taylor.s@gmail.com

## GitHub username

TaylorAmarelTech

## GitHub repository URL

https://github.com/TaylorAmarelTech/gemma4_comp

## OpenAI Organization ID

(paste yours from https://platform.openai.com/account/organization)

## Licensing

It's MIT, all the way through. The root LICENSE is MIT, and every one of the 18 packages sets license = MIT in its pyproject. The public datasets on Kaggle are open too (Creative Commons for the graded scores). Nothing is source-available or held back.

## Describe your role: are you a primary or core maintainer?

I'm the sole author and maintainer, and I've written every line of it. It started as one person's project and it still is: I do the commits, the releases, the tests, and the docs. The whole workspace (17 packages), the benchmark, the forced-labour indicator engine, the deterministic verifier, and the demo app are all mine.

## Why does this repository qualify?

I'll be honest: it doesn't have the stars or downloads you'd normally screen for. It's a one-person LLM safety project aimed at a problem most benchmarks skip, which is how models answer migrant workers who are in real danger. What it does have is reproducible evidence. The harness raises response quality by about 40 points out of 100 across eight different models, and every graded row is public, so anyone can check the number instead of taking my word for it.

## I'm interested in

All three: ChatGPT Pro with Codex for the day-to-day maintenance, Codex Security for the sensitive parts, and API credits to finish the evaluation.

## Why does your project need Codex Security?

It handles data you can't be casual with, like worker chats, ID numbers, and case details, and the whole design is that NGOs run it themselves, on their own machines. So the security actually has to hold. There's a hard anonymization gate before anything leaves the device, and an outbound allowlist that already caught an SSRF bug in the sync endpoint. Right now I'm the only one reviewing any of it. A second set of eyes on the anonymizer and the API surface would help a lot.

## How will you use API credits for your project?

Mostly to finish the evaluation. I'm grading the full 78,000-prompt set across every major model, but I run the judges on my own hardware and keep hitting quota limits, so it's been stalled for days at a time. Credits would let me actually complete the cross-model comparison instead of the slice I have, and take the tedious maintainer work off my plate: reviewing PRs, running the regression checks before release, and regenerating the public datasets and reports.

## Anything else we should know?

One thing worth saying: I built this for the Gemma 4 hackathon, but it was never really about Gemma. The same harness works on GPT-OSS, Llama, Qwen, and Mistral, whatever you point it at, and the improvement shows up on all of them. It's aimed at something every model gets wrong: sounding confident and helpful while handing someone in real danger advice that could get them hurt. It isn't popular yet. I genuinely think it should be.

## If a reviewer wants to dig in

Results, live: https://duecare-ai.com/evaluation (downloads at https://duecare-ai.com/data). Code: https://github.com/TaylorAmarelTech/gemma4_comp, starting with README.md and RESULTS.md. The numbers come from grading each response baseline versus harnessed, scored 0-100 by three different judge models across five safety dimensions, and a separate model-free checker agrees across all 78,719 prompts, so the result doesn't lean on any one judge.
