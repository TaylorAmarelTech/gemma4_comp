# Security Policy

## Reporting a vulnerability

Found a bug that puts migrant workers at risk? **Please don't open a
public GitHub issue.** Email the author privately:

> **amarel.taylor.s@gmail.com** — subject line `[duecare security]`

Expected response time: 72 hours acknowledgement, 14 days for a
substantive update on remediation.

## Scope — what we consider security-relevant

The Duecare framework is built around a hard PII gate (no raw PII
leaves the local process — see [`.claude/rules/10_safety_gate.md`](./.claude/rules/10_safety_gate.md)).
Bugs in the following classes are treated as security issues, not
ordinary bugs:

| Class | Examples |
|---|---|
| **PII leakage** | A code path that sends raw victim names, passport numbers, phone numbers, financial accounts, or content tagged as "personal" to an external service (HF Hub, Tavily, Brave, Serper, OpenClaw, browser tools, telemetry) |
| **Bypass of the safety harness** | A prompt or input pattern that causes the harness to silently drop GREP / RAG / Tools / Persona output before Gemma sees it |
| **Audit log gaps** | An outbound network call that bypasses `_audit()` in `fast_search.py`, allowing an outbound query to leave no trace |
| **Credential exposure** | Any code path where `HF_TOKEN`, BYOK keys (Tavily/Brave/Serper), or Kaggle credentials end up in logs / git / wheel artifacts / served HTTP responses |
| **Prompt injection** | An attacker-controlled string that, if pasted into the chat playground, can override the persona / disable harness toggles / extract the system prompt |
| **Wheel supply-chain** | Tampering with `_examples.json` / `_rubrics_*.json` / harness module that ships in the wheel |

## Non-security bugs

Functional bugs (e.g. a GREP rule has a bad regex, the cloudflared
tunnel times out, a notebook cell prints garbled output) are
ordinary bugs — open a regular issue at
[github.com/TaylorAmarelTech/gemma4_comp/issues](https://github.com/TaylorAmarelTech/gemma4_comp/issues).

## Coordinated disclosure

If you've found something that affects migrant workers in production
deployments, we'd appreciate 90 days of coordinated disclosure to give
NGO partners time to update their deployments. Earlier disclosure is
fine if you believe workers are at active risk.

## Hall of fame

Contributors who report security bugs are credited in `RESULTS.md`
(unless you'd prefer to remain anonymous).

---

> *"Privacy is non-negotiable. So the harness runs on your laptop."*
