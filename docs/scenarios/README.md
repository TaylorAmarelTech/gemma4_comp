# Deployment scenarios — persona-driven walkthroughs

> Pick the scenario that matches your role. Each links to the
> setup steps + day-to-day workflow + escalation paths.

## Index

| You are... | Read |
|---|---|
| **NGO director** running an office of 1-20 caseworkers | [`ngo-office-deployment.md`](./ngo-office-deployment.md) |
| **Caseworker** at an NGO that already deployed Duecare | [`caseworker_workflow.md`](./caseworker_workflow.md) |
| **Platform CTO** evaluating Duecare for enterprise rollout | [`enterprise_pilot.md`](./enterprise_pilot.md) |
| **Solo developer** evaluating the harness on a laptop | Skip these — go to [`docs/deployment_local.md`](../deployment_local.md) |
| **Trafficking-survivor advocate** wanting it on a phone | [`duecare-journey-android`](https://github.com/TaylorAmarelTech/duecare-journey-android) v0.7+ APK |

## What scenarios are NOT

These docs are **walkthroughs**, not specifications. They show one
sensible way to use Duecare for a given role. They're opinionated
about workflow, hardware, and tooling because too many choices
freezes a deployer.

If a scenario doesn't quite fit, the underlying primitives are all
documented in:

- [`docs/deployment_topologies.md`](../deployment_topologies.md) — five deployment shapes
- [`docs/cloud_deployment.md`](../cloud_deployment.md) — 13-platform cloud cookbook
- [`docs/considerations/`](../considerations/) — enterprise governance supplements
- [`docs/adr/`](../adr/) — why the architecture is what it is

Mix and match. The scenarios are starting points, not contracts.

## Common patterns across scenarios

Every scenario follows the same arc:

1. **Day 1 setup** (≤ 90 min) — bring up the stack, smoke-test, onboard the first user
2. **Day 2-7 operational rhythm** — morning health-check, weekly update pull
3. **Day 30 expansion checklist** — what to add once the workflow is stable
4. **When something breaks** — symptom → diagnostic → fix table

This shape comes from observing what actually works at NGOs that
adopt new tools: a 90-minute setup window is the operating budget,
the first week determines whether the tool sticks, and the first
month is when expansion (more caseworkers, more domains, more
integrations) starts to matter.

## Contributing a new scenario

If you've deployed Duecare in a different shape (academic research
lab, government regulator, religious-org legal clinic, journalist
investigative team), file a PR adding a scenario doc following the
same Day 1 / Day 2-7 / Day 30 / When-broken structure. The
underlying primitives are the same — your scenario is the
opinionated walkthrough that helps the next deployer in your
context skip a week of trial and error.
