# Financial Crime domain pack (adjacency proof)

DueCare's primary domain is **migrant-worker safety / human
trafficking** -- see `configs/duecare/domains/trafficking/`. The
trafficking pack already covers the financial-crime patterns that
appear inside migrant-worker exploitation (recruitment-fee
laundering, predatory recruitment loans, cross-border novation,
salary-deduction-as-racketeering -- look for the `fin_intersect_*`
ids in `trafficking/seed_prompts.jsonl`).

This pack exists as an **adjacency proof**: same `FileDomainPack`
implementation, same harness, same rubric structure, applied to
white-collar financial crime under FATF 40 Recommendations. It is
intended for partners who want to run DueCare's detection on
laundering / structuring / TBML / beneficial-ownership concealment
problems that are NOT routed through a migrant-worker case.

The primary product narrative remains migrant-worker protection.
