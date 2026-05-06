# Maintaining the Tool functions

> The Tools layer exposes 5 native function-calling lookups Gemma 4
> invokes when it needs structured data. This guide explains how to
> add a 6th tool, modify the 5 existing ones, and handle the schema
> contract.

## The 5 existing tools

| Tool name | Purpose | Returns |
|---|---|---|
| `lookup_corridor_fee_cap` | Look up the fee cap for an origin → destination corridor (16 corridors) | `{cap, currency, statute, jurisdiction}` |
| `lookup_fee_camouflage` | Decode a relabeled fee back to the underlying prohibited fee (25 labels) | `{actual_fee_type, prohibition_citation, severity}` |
| `lookup_ilo_indicator` | Get the description + citation for an ILO Forced Labour Indicator | `{number, name, description, source}` |
| `lookup_ngo_intake` | Find the NGO + hotline for a corridor (12 NGO groups) | `{ngo_name, phone, email, jurisdiction, intake_url}` |
| `lookup_ilo_convention` | Get the article-by-article summary of an ILO Convention (8 conventions) | `{number, title, articles, scope}` |

## Where the tools live

```
packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py
↓
def _tool_lookup_corridor_fee_cap(args: dict, table=None) -> dict:
    """..."""
    ...

_TOOL_DISPATCH = {
    "lookup_corridor_fee_cap":   _tool_lookup_corridor_fee_cap,
    "lookup_fee_camouflage":     _tool_lookup_fee_camouflage,
    "lookup_ilo_indicator":      _tool_lookup_ilo_indicator,
    "lookup_ngo_intake":         _tool_lookup_ngo_intake,
    "lookup_ilo_convention":     _tool_lookup_ilo_convention,
}
```

The corridor-cap, fee-camouflage, and NGO-intake tables are
in-code Python dicts. The plan is to migrate them to curator JSON
in v3.7 (same pattern as `_country_hints.json`).

## When the model calls a tool

```
USER PROMPT (e.g., "What is the fee cap for PH workers going to HK?")
    ↓
_tools_call(messages, ...) — Gemma 4's native function-calling API
    ↓
Gemma decides which tool to invoke + emits the tool-call JSON:
  {
    "name": "lookup_corridor_fee_cap",
    "arguments": {"origin": "Philippines", "destination": "Hong Kong",
                  "sector": "domestic"}
  }
    ↓
_TOOL_DISPATCH[name](arguments)
    ↓
{"cap": "0.00", "currency": "HKD",
 "statute": "POEA MC 14-2017",
 "jurisdiction": "PH"}
    ↓
Result is appended to Gemma's context as a `tool` message; Gemma
generates the final response citing the result.
```

## Tool function contract

Every tool function:

```python
def _tool_lookup_X(args: dict, table=None) -> dict:
    """Tool function. Receives the model's tool-call args dict;
    returns a structured result dict.

    The `table` kwarg lets the caller pass a custom dict instead
    of the bundled one (used for testing + per-request user-added
    catalogs)."""
    if not isinstance(args, dict):
        return {"error": f"args must be a dict, got {type(args).__name__}"}
    # Validate args
    origin = args.get("origin")
    destination = args.get("destination")
    if not origin or not destination:
        return {"error": "missing required args: origin, destination"}
    # Look up
    table = table or DEFAULT_CORRIDOR_TABLE
    key = (origin.lower(), destination.lower())
    if key not in table:
        return {"error": f"corridor not found: {origin}→{destination}",
                "available": list(table.keys())[:10]}
    return table[key]
```

**Rules:**
1. **Always return a dict.** Never None; never raise (except
   ValidationError which the caller handles).
2. **Validate args.** Don't trust the model — return `{"error": ...}`
   on bad input.
3. **Surface "available" alternatives** when a lookup misses.
   Helps the model recover.
4. **Use the `table` kwarg pattern** so users can extend via
   `custom_corridor_caps` per-request without touching the bundled
   table.

## Adding a 6th tool

Example: a `lookup_court_decision` tool for binding court precedents.

### Step 1: Implement the function

```python
def _tool_lookup_court_decision(args: dict, table=None) -> dict:
    """Look up a binding court decision by jurisdiction + topic.

    Args:
      jurisdiction: ISO country code (e.g. "HK", "PH", "SG")
      topic: high-level topic (e.g. "passport_retention",
             "fee_recovery", "joint_and_several_liability")

    Returns:
      {case_name, citation, year, holding, jurisdiction, source_url}
    """
    if not isinstance(args, dict):
        return {"error": f"args must be a dict"}
    jurisdiction = args.get("jurisdiction", "").upper()
    topic = args.get("topic", "").lower()
    if not jurisdiction or not topic:
        return {"error": "missing args: jurisdiction, topic"}
    table = table or COURT_DECISION_TABLE
    key = (jurisdiction, topic)
    if key not in table:
        nearby = [k for k in table if k[0] == jurisdiction]
        return {"error": f"no decision for {jurisdiction}/{topic}",
                "available_topics_in_jurisdiction": nearby}
    return table[key]
```

### Step 2: Register in `_TOOL_DISPATCH`

```python
_TOOL_DISPATCH = {
    "lookup_corridor_fee_cap":   _tool_lookup_corridor_fee_cap,
    "lookup_fee_camouflage":     _tool_lookup_fee_camouflage,
    "lookup_ilo_indicator":      _tool_lookup_ilo_indicator,
    "lookup_ngo_intake":         _tool_lookup_ngo_intake,
    "lookup_ilo_convention":     _tool_lookup_ilo_convention,
    "lookup_court_decision":     _tool_lookup_court_decision,  # NEW
}
```

### Step 3: Add to the tools catalog (Gemma's tool list)

```python
def _build_tools_catalog() -> list:
    return [
        ...
        {
            "name": "lookup_court_decision",
            "description": "Look up a binding court decision by "
                          "jurisdiction + topic. Returns the case name, "
                          "citation, year, holding, and source URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "jurisdiction": {
                        "type": "string",
                        "description": "ISO country code (e.g. 'HK', 'PH')"
                    },
                    "topic": {
                        "type": "string",
                        "description": "High-level topic (e.g. 'passport_retention')"
                    }
                },
                "required": ["jurisdiction", "topic"]
            }
        }
    ]
```

### Step 4: Add the lookup table

```python
COURT_DECISION_TABLE = {
    ("HK", "passport_retention"): {
        "case_name":   "FACV 2/2008 — Vallejos & Domingo v Commissioner of Registration",
        "citation":    "[2013] 4 HKLRD 343",
        "year":        2013,
        "holding":     "...",
        "jurisdiction": "HK",
        "source_url":  "https://...",
    },
    ...
}
```

### Step 5: Add a test

```python
def test_lookup_court_decision_tool() -> None:
    h = _load_harness()
    result = h._tool_lookup_court_decision({
        "jurisdiction": "HK",
        "topic": "passport_retention"
    })
    assert "case_name" in result
    assert "citation" in result
```

### Step 6: Update `verify.py`

Bump the threshold:
```python
Check("Tools",  "duecare.chat.harness", "_TOOL_DISPATCH",  6,  # was 5
      "lookup functions"),
```

### Step 7: PR

Reviewer: jurist for the case selection + methodologist for the
return-shape design.

## Per-request user extensions

Users can add custom corridor caps / fee-camouflage labels / NGO
intakes via the chat UI's "Custom catalog" editor (persisted in
`localStorage`, sent per-request via `HarnessToggles.custom_*`).
The server merges the custom catalog with the bundled one before
calling the tool function.

This means:
- Bundled catalog ships with the wheel
- Custom additions live in the user's browser
- Sensitive corridor data (e.g., a specific NGO's case-protocol
  hotline that shouldn't be public) can be added without a PR

## Common pitfalls

1. **Returning the wrong shape.** Tools that return free-form prose
   instead of a dict break Gemma's tool-call parsing. Always return
   a dict.

2. **Not handling missing args.** If the model calls with bad args,
   return `{"error": ...}` so the model can recover. Raising an
   exception aborts the whole chat call.

3. **Hard-coded table without `table` kwarg.** Breaks user
   extensibility. Always accept the optional `table` kwarg.

4. **Forgetting to register in `_TOOL_DISPATCH`.** The function
   exists but Gemma can't dispatch to it.

5. **Forgetting to add to `_build_tools_catalog`.** Gemma doesn't
   know the tool exists, so won't call it.

## See also

- [`../component_diagram.md`](../component_diagram.md) — how Tools
  fits in the request flow (after persona/GREP/RAG, before final
  Gemma generation)
- [`../EXTENDING.md`](../EXTENDING.md) — for adding whole new
  domains (which often add new tools)
