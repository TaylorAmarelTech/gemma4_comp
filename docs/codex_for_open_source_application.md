# Codex for Open Source - application answers (DueCare)

The four capped fields are all under 500 characters. Everything here is true and you can check it in the repo. There is also an HTML version with copy buttons at docs/codex_application.html.

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

It's MIT, all the way through. The root license and all 18 packages. The public datasets are open too. Nothing is locked up or held back. Take it, fork it, run it, build on it.

## Describe your role: are you a primary or core maintainer?

Yes, I'm the primary maintainer. It's a solo project at the moment, so that means the code, the tests, the releases, and the docs, and reviewing everything before it goes in. I'd genuinely welcome other people working on it, but for now the maintenance runs through me.

## Why does this repository qualify?

Here's the truth: nobody's starring this repo, and I get why. But picture a domestic worker whose passport was just taken, asking a chatbot what to do. It answers warmly, confidently, and sends her somewhere that could get her hurt. That's the gap I've spent months closing. I can't show you a download count. I can show you that across eight different models the answers get far safer and more useful, and every graded example is public, so you can read them and judge for yourself.

## I'm interested in

All three. ChatGPT Pro with Codex for the everyday work, Codex Security for the parts where I can't afford to be wrong, and API credits to finish the evaluation.

## Why does your project need Codex Security?

This isn't a toy. People's safety runs through it. It touches the most sensitive things a person has: their messages, their ID, the details of how they're being exploited. The whole point is that a small NGO can run it on a laptop without handing that to anyone. I built the guardrails I know how to: a gate that strips personal data before it leaves the machine, an allowlist that already caught a real hole. But I'm one person. I'd sleep better with someone else checking my work first.

## How will you use API credits for your project?

To finish the work, honestly. I'm testing this across every major model on 78,000 real scenarios, but I run it on my own hardware and keep running out of capacity. It's been frozen for days right now because I hit a limit. Credits would let me finish the comparison I started, and hand off the grind, the code reviews, the release checks, so I can put my time where it counts: making the answers better for the people who actually need them.

## Anything else we should know?

One last thing. I made this for a Gemma hackathon, but it was never about winning, or about one model. It works on all of them, GPT-OSS, Llama, Qwen, Mistral. It's about a failure they share: being warmly, confidently wrong with someone whose life is on the line. Almost nobody knows this project exists. I think they should, not for my sake, but because this problem deserves the attention and almost no one is working on it.

## If a reviewer wants to dig in

The results are live at https://duecare-ai.com/evaluation, with the downloads at https://duecare-ai.com/data. The code is at https://github.com/TaylorAmarelTech/gemma4_comp, and README.md and RESULTS.md are the place to start. Every number comes from grading each answer twice, the model on its own and the model with the harness, scored by three separate judge models across five safety dimensions. A separate checker that uses no model at all agrees across all 78,719 scenarios, so none of it rests on a single judge.
