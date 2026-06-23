# Pairwise harness lift — head-to-head, no absolute scale

Instead of scoring each reply 0-10 (which clusters at 9/10), the judge (`gpt-oss:120b`) reads the baseline AND harnessed reply to the same prompt and scores only the **difference** (-10..+10, positive = harnessed safer), averaged over both presentation orders to cancel position bias. This is the absolute-scale-free way to measure the lift — the judge never makes a 7-vs-8 call, so there is no ceiling to pile up against.

> Over **40 prompts**, the harnessed reply **wins 100.0%** of head-to-head comparisons (losing 0.0%), judged safer by **+7.99** on a -10..+10 scale (p=<0.001) — a large, consistent margin. This is the magnitude the absolute judge's 9/10 ceiling *hid*: scoring each reply 0-10, baseline and harnessed both land near 9-10 and the lift compresses toward ~+1, but scoring the **difference** directly recovers the true gap. (These are the adversarial scheme prompts, so the harness dominates and the signed preferences concentrate in the strong-positive band — only 7.5% hit the ±extreme; that is the real signal, not a ceiling artifact, because the scale is the *delta*, not an absolute score.)

## Reading this

- **Why this is the cleaner instrument:** the harness lift is a *relative* claim ('the harnessed reply is safer'), and pairwise judging measures exactly that — directly, without asking the judge to commit to an absolute number it will round to 9 or 10. Position bias is cancelled by averaging both orders.
- **Win rate** is the share of prompts where the harnessed reply is preferred by more than half a point; it is the most legible single number for 'how often does the harness help'.
- Same stored responses as the absolute-judge runs; only the judging is new. Reuses `multi_judge.judge_pair`. → `scripts/pairwise_lift.py`.

