# Deployment scenarios — persona-driven walkthroughs

> Pick the scenario that matches your role. Each links to the
> setup steps + day-to-day workflow + escalation paths.

## Index — by persona

| You are... | Read |
|---|---|
| **OFW / migrant worker** wanting it on your phone for self-protection | [`worker-self-help.md`](./worker-self-help.md) (English) · [Tagalog draft](./translations/worker-self-help.tl.md) · [Spanish draft](./translations/worker-self-help.es.md) |
| **Caseworker** at an NGO that already deployed Duecare | [`caseworker_workflow.md`](./caseworker_workflow.md) |
| **NGO director** running an office of 1-20 caseworkers | [`ngo-office-deployment.md`](./ngo-office-deployment.md) |
| **Legal aid lawyer** preparing a case from intake | [`lawyer-evidence-prep.md`](./lawyer-evidence-prep.md) |
| **Government regulator** triaging complaints + spotting patterns | [`regulator-pattern-analysis.md`](./regulator-pattern-analysis.md) |
| **Embassy / consulate officer** protecting nationals abroad | [`embassy-consular.md`](./embassy-consular.md) |
| **ILO / IOM / OHCHR regional staff** doing supra-national analysis | [`ilo-iom-regional.md`](./ilo-iom-regional.md) |
| **Recruitment agency compliance officer** doing self-audit | [`recruiter-self-audit.md`](./recruiter-self-audit.md) |
| **Individual researcher** (academic / NGO research) | [`researcher-analysis.md`](./researcher-analysis.md) |
| **Investigative journalist** covering trafficking / recruitment fraud | [`journalist-investigation.md`](./journalist-investigation.md) |
| **IT director** at a 50-500 person org evaluating ops + TCO | [`it-director.md`](./it-director.md) |
| **Chief architect** designing the integration | [`chief-architect.md`](./chief-architect.md) |
| **VP of Engineering** at a product org adopting it broadly | [`vp-engineering.md`](./vp-engineering.md) |
| **Platform CTO** at Big Tech evaluating a 30-day pilot | [`enterprise_pilot.md`](./enterprise_pilot.md) |
| **Solo developer** evaluating the harness on a laptop | Skip these — go to [`docs/deployment_local.md`](../deployment_local.md) |

## Index — by deployment shape

| Topology | Personas that fit |
|---|---|
| Topology D (on-device only) — Android app | OFW / migrant worker |
| Topology B (NGO-office edge) — Mac mini / NUC on the LAN | NGO director, caseworker, legal aid lawyer, recruitment-agency compliance officer, regulator (small unit) |
| Topology C (server + thin clients) — cloud / k8s | IT director, chief architect, VP of Engineering, CTO, regulator (national-scale) |
| Topology A (single-component local) | Individual researcher, solo developer |
| Topology E (hybrid edge LLM + cloud knowledge) | NGO with frequent rule updates needed in the field |

## Index — by what you'll spend

| Persona | Hardware / cloud | One-time | Monthly | Year-1 staff time |
|---|---|---:|---:|---|
| OFW | Android phone (existing) | $0 | $0 | n/a |
| Caseworker | uses NGO's deployment | $0 | $0 | n/a |
| NGO director | Mac mini M2 | $250-800 | $0-25 | ~30 min/wk |
| Legal aid lawyer | NGO's deployment OR own Mac mini | $0-800 | $0-25 | ~30 min/wk |
| Researcher | Laptop | $0 | $0-25 | ~10h to publish a result |
| IT director | Mac mini OR small cloud server | $0-800 | $0-130 | ~30 min/wk |
| Recruitment compliance | Mac mini | $250-800 | $0-25 | ~8 hrs/quarter |
| Regulator (unit) | Mac mini | $250-800 | $0-25 | ~30 min/wk |
| Regulator (national) | Cloud + k8s | $0 | $1500-10k | 0.5-1 FTE |
| Chief architect | n/a (designing) | $0 | $0 | ~20-40 hrs to design |
| VP Engineering | Cloud + k8s | $0 | $300-1500 | 1.5 FTE for a quarter |
| Platform CTO | Cloud + k8s + vendor mgmt | $0 | $1500-15k | 1-2 FTE |

## Common patterns across scenarios

Every persona-driven scenario follows the same arc:

1. **Day 1 setup** (≤ 90 min for users; ≤ 6 weeks for engineering teams)
2. **Day 2-7 operational rhythm** — what the daily / weekly use looks like
3. **Day 30 expansion checklist** — what to add once it's stable
4. **When something breaks** — symptom → diagnostic → fix table

This shape comes from observing what actually works at NGOs / clinics
/ enterprises that adopt new tools: a 90-minute setup window is the
operating budget, the first week determines whether the tool sticks,
and the first month is when expansion (more users, more domains, more
integrations) starts to matter.

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

## Personas we don't cover (yet)

If you're one of these and Duecare seems relevant, file a PR
adding a scenario doc:

- **Investigative journalist** (close to "individual researcher" but
  with editorial / source-protection considerations)
- **Trafficking survivor** seeking documentation of past abuse for a
  current legal case (close to "OFW" but post-exploitation)
- **University labor-studies professor** running a class exercise
- **Religious-org legal clinic** (close to "legal aid lawyer")
- **Worker-cooperative recruitment** (close to "recruitment-agency
  compliance" but adversarial to traditional fee-charging recruiters)
- **Embassy consular officer** handling worker complaints in the
  destination country (close to "regulator" but no enforcement power)
- **International labor organization staff** (ILO regional office,
  IOM, OHCHR) doing pattern analysis at supra-national scale

Each of these has different constraints (privilege, source
protection, jurisdiction, mandate). The underlying tooling supports
all of them; the scenario doc is what helps the next person in
that role skip a week of trial and error.

## Contributing a new scenario

1. Copy [`worker-self-help.md`](./worker-self-help.md) (smallest
   scenario) or [`ngo-office-deployment.md`](./ngo-office-deployment.md)
   (most thorough) as a starting template.
2. Fill in the persona's actual concerns in their language.
3. Add Day 1 / Day 2-7 / Day 30 / When-broken sections.
4. Add a row to the index above.
5. PR — include the persona's name + role in the description.
