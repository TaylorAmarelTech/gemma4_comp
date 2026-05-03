# Generators — purpose

**Module id:** `duecare.tasks.generators`

## One-line

DueCare prompt-mutation generators.

## Long-form

DueCare prompt-mutation generators.

Usage::

    from duecare.tasks.generators import (
        EvasionGenerator,
        CoercionGenerator,
        FinancialGenerator,
        RegulatoryGenerator,
        CorridorGenerator,
        ALL_GENERATORS,
    )

    prompts = [{"id": "p1", "text": "...", "category": "fee_evasion"}]
    for gen in ALL_GENERATORS:
        variations = gen.generate(prompts, n_variations=2, seed=42)

## See also

- [`AGENTS.md`](AGENTS.md) — agentic instructions for AI readers
- [`HIERARCHY.md`](HIERARCHY.md) — position in the module tree
- [`STATUS.md`](STATUS.md) — completion state and TODO list
