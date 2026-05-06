# Maintaining the persona library

> The persona is the system prompt that defines the assistant's
> role, expertise, and answering style. Duecare ships a default
> 40-year anti-trafficking expert persona; this guide explains how
> to add new personas (NGO-mode, lawyer-mode, regulator-mode, etc.)
> and how to maintain the existing one.

## Where the persona lives

**Default persona** (in code, not curator JSON yet):

```
packages/duecare-llm-chat/src/duecare/chat/app.py
↓
DEFAULT_PERSONA = """You are an international anti-trafficking..."""
```

**User-supplied persona** (per-request override):

```
POST /api/chat/send
{
  "messages": [...],
  "toggles": {
    "persona": true,
    "persona_text": "Your custom persona here..."   ← user override
  }
}
```

The `persona_text` field is stored client-side in `localStorage` so
it persists across page reloads.

## When to edit the default persona

The default persona ships in every wheel. Edit it when:

- A new ILO Convention becomes relevant (add to the framework list)
- A new corridor + statute is added to the harness (add to the
  controlling-instrument list)
- A new exploitation pattern is well-documented (add to the
  recruiter-tactics list)
- Behavior should be tuned globally (e.g., increase emphasis on
  Palermo Art. 3(b) consent-irrelevance)

## How to edit the default persona

1. Open `packages/duecare-llm-chat/src/duecare/chat/app.py`
2. Find `DEFAULT_PERSONA = """..."""`
3. Edit the prose — it's plain text. No template variables.
4. Run the affected tests:
   ```bash
   pytest packages/duecare-llm-chat/tests/test_harness_behavior.py
   pytest packages/duecare-llm-chat/tests/test_harness_v3_6.py
   ```
5. PR with:
   - One-line summary
   - Citation/source for any legal claim added
   - Reviewer: jurist OR methodologist (depending on the change)

## How to ship a new persona variant

For deployments that need a different persona (e.g. lawyer-mode,
regulator-mode, journalist-mode), there are three paths:

### Path 1: Per-request override (simplest)

The client sends `persona_text` per-request. Persistent in
`localStorage`. No server changes needed.

**Example** — NGO-caseworker persona:

```javascript
// In your client code (or pasted into the chat UI's persona editor)
const NGO_CASEWORKER_PERSONA = `You are an experienced NGO
caseworker handling intake for migrant-worker trafficking cases.

Your priorities:
1. Document each case with: corridor, ILO indicators present,
   recruiter/employer details, fees paid + receipts, current
   location.
2. Recognize the worker's agency and constraints — never paternalise.
3. Provide concrete next steps: NGO intake hotline, complaint
   procedure, possible refund pathway, shelter options.
4. Cite the specific statute violated AND the article number.
...`;
```

### Path 2: Persona registry curator block (planned, v3.7)

A new curator-block JSON file `_personas.json`:

```json
{
  "schema": "duecare-personas/v1",
  "version": "1.0.0",
  "personas": [
    {
      "id": "default_anti_trafficking_expert",
      "name": "Anti-trafficking expert (40-year)",
      "audience": "general",
      "text": "You are an international anti-trafficking..."
    },
    {
      "id": "ngo_caseworker",
      "name": "NGO caseworker (intake mode)",
      "audience": "ngo_intake",
      "text": "You are an experienced NGO caseworker..."
    },
    {
      "id": "lawyer_brief_research",
      "name": "Lawyer (brief research mode)",
      "audience": "lawyer_research",
      "text": "You are a research lawyer..."
    }
  ]
}
```

Then `/api/personas` would return the catalog and the chat UI
would have a persona dropdown. The `audience` field could optionally
auto-select based on the prompt classifier.

**Status: planned for v3.7.** Until then, use Path 1 or Path 3.

### Path 3: Fork the default

If your deployment is single-purpose (e.g. a regulator-only
dashboard), you can fork `app.py` and replace `DEFAULT_PERSONA`.

## Style + content checklist

A good persona:

- **Names the role clearly.** "You are an international
  anti-trafficking expert with 40 years of experience" beats "You
  are a helpful assistant."
- **Lists the legal frameworks the assistant should cite.** ILO C029,
  C181, etc. by number. Reduces hallucination.
- **Explicitly forbids harmful patterns.** "DO NOT provide
  operational optimization advice for any scheme containing
  trafficking indicators."
- **Specifies the answer shape.** "First identify red flags. Then
  cite the convention article + national statute by section. Then
  refer to the corridor's NGO."
- **Acknowledges limits.** "If the Duecare safety harness has fired,
  use that output to ground every claim."

A bad persona:

- Generic ("You are helpful")
- Verbose without specifics ("You know about labor law")
- Operator-side framing ("Help the recruiter optimize fees")
- Encourages refusal-without-grounding ("Refuse if anything seems off")

## Length

The default persona is ~2,500 characters. Persona text is prepended
to every message Gemma sees, which:

- Counts toward the context window (E4B = 32K tokens; 2,500 chars
  ≈ 600 tokens — fine)
- Affects every generation's latency by ~50ms
- Should be terse-but-specific. Bullet lists work better than prose.

## Testing a new persona

1. Load the persona via the chat UI's persona editor (Settings ▶
   Edit persona)
2. Send the canonical 5 high-impact demo prompts (jailbreak / online
   demo / model comparison / social-eng / headline lift)
3. Check the response:
   - Does it cite specific statute + article numbers?
   - Does it refuse + name the violation, not bare-refuse?
   - Does it provide concrete next steps?
4. Run `/api/grade?mode=universal` on each response and verify
   pct_score is similar to the default-persona baseline (within
   ±5pp).

## See also

- [`grep_rules.md`](grep_rules.md) — how to add a new GREP rule
  (different persona may need different rules)
- [`../contributing_curator_blocks.md`](../contributing_curator_blocks.md)
  — for curator JSON edits
- [`../component_diagram.md`](../component_diagram.md) — how the
  persona layer fits with GREP / RAG / Tools / Online
