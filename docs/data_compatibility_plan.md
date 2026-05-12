# DueCare data compatibility plan (2026-05-12)

> Action doc paired with `docs/data_primitives.md` (canonical
> shapes) and `docs/data_surface_inventory.md` (full surface
> list). This file is the **concrete refactor checklist** — each
> entry shows the exact code change needed to bring a kernel back
> to canonical, plus the proposed `duecare.appendix_primitives`
> helper module that future kernels import to prevent regression.
>
> Different scope from `docs/compatibility.md` (which covers
> Python / OS / hardware). This file is **data-shape compatibility
> across kernels and the website**.

## Execution order (tiered)

| Tier | Items | Severity | Effort | When |
|---|---|---|---|---|
| 1 | A-04 schema_version drift; A-19 / A-20 missing RunID | MEDIUM | small | before submission |
| 2 | `aggregate` -> `summary` rename (×4); per-row name rename (×3); missing `error` field (×2); A-11 flatten | LOW | small per kernel | this week |
| 3 | Build `duecare.appendix_primitives` helper module; migrate kernels one-at-a-time | LOW | medium | post-submission |
| 4 | Extend audit script `validate_public_surface.py` with `bundle_envelope_v1` check | LOW | small | post-submission |

## Tier 1 — must fix before submission

### 1.1 A-04 schema_version drift

**Current (drift):** `kaggle/A-06-prompt-generation/kernel.py`
emits `"schema_version": "duecare.a04_handoff.v1"`.

**Canonical:** `"schema_version": "1.0"` plus a separate
`"handoff_kind": "synth_data_to_trainer"` field to preserve the
semantic identifier.

**Diff (illustrative, in the kernel's handoff-emit block):**

```python
# BEFORE
manifest = {
    "schema_version": "duecare.a04_handoff.v1",
    "producer_notebook": "A-04-synthetic-data-generator",
    "consumer_notebook": "A-05-fine-tune-trainer",
    ...
}

# AFTER
manifest = {
    "schema_version": "1.0",
    "handoff_kind": "synth_data_to_trainer",
    "producer_notebook": "A-04-synthetic-data-generator",
    "consumer_notebook": "A-05-fine-tune-trainer",
    ...
}
```

**Consumer-side guard (A-05 trainer parser, transitional):**

```python
sv = manifest.get("schema_version", "")
if sv in ("1.0", "duecare.a04_handoff.v1"):
    pass   # accept either during the rollover
else:
    raise SystemExit(f"unsupported schema_version: {sv}")
```

### 1.2 A-19 / A-20 missing RunID

**Current (drift):** Both kernels emit fixed-name bundles:

- `a19_multilingual_bundle.zip`
- `a20_privacy_boundary_bundle.zip`

**Canonical:** every JSON-emitting kernel writes
`<RUN>_bundle.zip` with a unique RunID per session.

**Diff for A-19 (`kaggle/A-19-multilingual-demo/kernel.py`):**

```python
# Add near the OUTPUT_DIR / CONFIG section:
import time
_run_ts = time.strftime("%Y-%m-%dT%H-%M-%SZ", time.gmtime())
RUN_ID = f"a19_multilingual_{_run_ts}"

# Replace:
RESULTS_PATH = OUTPUT_DIR / "a19_multilingual_demo.json"
BUNDLE_PATH = OUTPUT_DIR / "a19_multilingual_bundle.zip"

# With:
RESULTS_PATH = OUTPUT_DIR / f"{RUN_ID}_multilingual_demo.json"
BUNDLE_PATH = OUTPUT_DIR / f"{RUN_ID}_bundle.zip"
```

**Diff for A-20:** same pattern; slot is `a20_privacy_{...}`.

## Tier 2 — should fix this week

### 2.1 Rename `aggregate` -> `summary` (×4)

Kernels using `aggregate` as a top-level field name should rename
to `summary` to match canonical. Semantic content is identical.

Affected: A-03, A-08 (compare kernels), A-14 (UGC moderator),
A-15 (NGO local-KB).

```python
# BEFORE
payload = {
    "schema_version": "1.0",
    "kernel_id": "a-14-ugc-batch-moderator",
    "run_id": RUN_ID,
    "config": {...},
    "metadata": {...},
    "aggregate": _aggregate(),
    "results": RESULTS,
}

# AFTER
payload = {
    "schema_version": "1.0",
    "kernel_id": "a-14-ugc-batch-moderator",
    "run_id": RUN_ID,
    "config": {...},
    "metadata": {...},
    "summary": _aggregate(),
    "results": RESULTS,
}
```

**Consumer migration (A-03 / A-08 + any reader):** accept BOTH
during rollover:

```python
summary = payload.get("summary") or payload.get("aggregate") or {}
```

### 2.2 Rename per-row arrays -> `results[]` (×3)

Affected:

- A-15 NGO local-KB: `ingested[]` -> `results[]`
- A-16 pack builder: `packs_built[]` -> `results[]`
- A-17 sentinel: `proposals[]` -> `results[]`

```python
# BEFORE (A-17)
payload = {
    ...,
    "summary": {"n_proposals": len(PROPOSALS), ...},
    "proposals": PROPOSALS,
}

# AFTER
payload = {
    ...,
    "summary": {"n_results": len(PROPOSALS), ...},
    "results": PROPOSALS,
}
```

The downstream `/api/state` endpoints in those kernels also
reference `proposals[]` / `ingested[]` / `packs_built[]` — update
the HTML render functions to read `results[]`.

### 2.3 Add `error: null` defaults to A-10 + A-15 rows

A-10 composite rows and A-15 ingested rows currently omit the
`error` field on success. Add `"error": None` as the default:

```python
# A-10 _render_composite return:
return {
    "composite_id": ...,
    "scenario": ...,
    ...,
    "error": None,
}

# A-15 ingest_case return:
return {
    "case_id": ...,
    "content_redacted": ...,
    ...,
    "error": None,
}
```

### 2.4 Flatten A-11 `results.{fine_tuned, stock}` -> flat `results[]`

**Current:** `payload["results"]` is a dict with two arrays.

**Canonical:** flat `results[]` with each row carrying a
`condition` field:

```python
# BEFORE
"results": {
    "fine_tuned": _finetuned_rows,
    "stock":      _stock_rows,
}

# AFTER
flat = []
for r in _finetuned_rows:
    flat.append({**r, "condition": "fine_tuned"})
for r in _stock_rows:
    flat.append({**r, "condition": "stock"})
"results": flat,
```

Downstream filter: `results.filter(r => r.condition === 'stock')`.

## Tier 3 — long-term enforcement: `duecare.appendix_primitives`

A new module shipped inside `packages/duecare-llm-chat/`:

```
packages/duecare-llm-chat/src/duecare/appendix_primitives/
├── __init__.py        # re-exports the public API
├── envelopes.py       # BundleEnvelope, PerRow, HarnessTrace Pydantic
├── ids.py             # make_run_id() canonical generator
├── io.py              # write_v1_bundle, read_v1_bundle
├── audit.py           # validate_canonical(bundle_dict)
└── tests/
    ├── test_envelopes.py
    ├── test_ids.py
    ├── test_io.py
    └── test_audit.py
```

### Public API

```python
from duecare.appendix_primitives import (
    make_run_id,
    BundleEnvelope,
    PerRow,
    HarnessTrace,
    write_v1_bundle,
    read_v1_bundle,
    validate_canonical,
)
```

### Pydantic model sketches

```python
# envelopes.py
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class HarnessLayerStats(BaseModel):
    enabled: bool
    elapsed_ms: float = 0.0


class HarnessGrep(HarnessLayerStats):
    rules_evaluated: int = 0
    rules_fired: list[dict[str, Any]] = Field(default_factory=list)


class HarnessRag(HarnessLayerStats):
    top_k: int = 5
    docs_retrieved: list[dict[str, Any]] = Field(default_factory=list)


class HarnessTools(HarnessLayerStats):
    tools_called: list[dict[str, Any]] = Field(default_factory=list)


class HarnessOnline(HarnessLayerStats):
    queries: list[str] = Field(default_factory=list)


class HarnessTrace(BaseModel):
    persona: dict[str, Any] = Field(
        default_factory=lambda: {"enabled": False})
    grep:    HarnessGrep    = Field(default_factory=HarnessGrep)
    rag:     HarnessRag     = Field(default_factory=HarnessRag)
    tools:   HarnessTools   = Field(default_factory=HarnessTools)
    online:  HarnessOnline  = Field(default_factory=HarnessOnline)
    merged_prompt_chars: int = 0


class PerRow(BaseModel):
    row_id:        str
    prompt_text:   str
    response:      str
    elapsed_s:     float = 0.0
    tokens_in:     int   = 0
    tokens_out:    int   = 0
    harness_trace: Optional[HarnessTrace] = None
    citations:     list[str] = Field(default_factory=list)
    error:         Optional[str] = None
    model_config = {"extra": "allow"}


class BundleEnvelope(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    kernel_id:      str
    run_id:         str
    config:         dict[str, Any] = Field(default_factory=dict)
    metadata:       dict[str, Any] = Field(default_factory=dict)
    summary:        dict[str, Any] = Field(default_factory=dict)
    results:        list[PerRow]   = Field(default_factory=list)
    model_config = {"extra": "allow"}
```

### make_run_id() sketch

```python
# ids.py
import time


def make_run_id(slot: str, purpose: str, variant: str = "",
                  iso_ts: str | None = None) -> str:
    """Canonical RunID generator.

    Examples:
      make_run_id("a01", "stock", "e2b-it")
      -> 'a01_e2b-it_stock_2026-05-12T19-30-00Z'

      make_run_id("a15", "local_kb")
      -> 'a15_local_kb_2026-05-12T19-30-00Z'
    """
    ts = iso_ts or time.strftime("%Y-%m-%dT%H-%M-%SZ", time.gmtime())
    parts = [slot]
    if variant:
        parts.append(variant)
    parts.append(purpose)
    parts.append(ts)
    return "_".join(parts)
```

### write_v1_bundle() sketch

```python
# io.py
import hashlib
import json
import zipfile
from pathlib import Path

from .envelopes import BundleEnvelope


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def write_v1_bundle(envelope: BundleEnvelope,
                     output_dir: Path) -> dict:
    """Validate envelope + write the 4-file v1.0 bundle."""
    run_id = envelope.run_id
    results_path  = output_dir / f"{run_id}_results.json"
    jsonl_path    = output_dir / f"{run_id}_run.jsonl"
    metadata_path = output_dir / f"{run_id}_metadata.json"
    bundle_path   = output_dir / f"{run_id}_bundle.zip"

    full = envelope.model_dump(mode="json")
    results_path.write_text(
        json.dumps(full, indent=2, ensure_ascii=False), "utf-8")
    metadata_only = {k: v for k, v in full.items() if k != "results"}
    metadata_path.write_text(
        json.dumps(metadata_only, indent=2, ensure_ascii=False),
        "utf-8")
    with jsonl_path.open("w", encoding="utf-8") as fh:
        for row in full["results"]:
            fh.write(json.dumps({
                "schema_version": "1.0",
                "run_id": run_id,
                "kernel_id": envelope.kernel_id,
                **row,
            }, ensure_ascii=False) + "\n")

    manifest = {
        "schema_version": "1.0",
        "run_id":     run_id,
        "kernel_id":  envelope.kernel_id,
        "files":      ["results.json", "run.jsonl", "metadata.json"],
        "checksums": {
            "results.json":  _sha256(results_path),
            "run.jsonl":     _sha256(jsonl_path),
            "metadata.json": _sha256(metadata_path),
        },
    }
    with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))
        zf.write(results_path,  "results.json")
        zf.write(jsonl_path,    "run.jsonl")
        zf.write(metadata_path, "metadata.json")

    return {
        "results_json":  results_path,
        "run_jsonl":     jsonl_path,
        "metadata_json": metadata_path,
        "bundle_zip":    bundle_path,
        "manifest":      manifest,
    }
```

### validate_canonical() sketch

```python
# audit.py
from typing import Any
from .envelopes import BundleEnvelope


def validate_canonical(bundle: dict[str, Any]) -> list[str]:
    """Return a list of drift findings; empty list = canonical."""
    findings: list[str] = []
    if bundle.get("schema_version") != "1.0":
        findings.append(
            f"schema_version drift: {bundle.get('schema_version')!r} "
            f"(expected '1.0')")
    if "summary" not in bundle and "aggregate" in bundle:
        findings.append(
            "uses 'aggregate' instead of canonical 'summary'")
    if "results" not in bundle:
        for alt in ("ingested", "proposals", "packs_built"):
            if alt in bundle:
                findings.append(
                    f"uses '{alt}[]' instead of canonical 'results[]'")
    try:
        BundleEnvelope.model_validate(bundle)
    except Exception as e:
        findings.append(
            f"BundleEnvelope validation: "
            f"{type(e).__name__}: {str(e)[:200]}")
    return findings
```

### Kernel migration recipe

Once `duecare.appendix_primitives` is shipped, each kernel
migrates to:

```python
from duecare.appendix_primitives import (
    make_run_id, BundleEnvelope, PerRow, write_v1_bundle,
)

RUN_ID = make_run_id("a14", "ugc", GEMMA_MODEL_VARIANT)

rows: list[PerRow] = []
for r in scored:
    rows.append(PerRow(
        row_id=r["post_id"],
        prompt_text=r["text"],
        response=r["analysis"],
        elapsed_s=r["elapsed_ms"] / 1000.0,
        citations=r["citations"],
        error=r.get("error"),
        # kernel-specific extras carried via model_config extra=allow:
        risk_score=r["risk_score"],
        verdict=r["verdict"],
        indicators=r["indicators"],
    ))

envelope = BundleEnvelope(
    kernel_id="a-14-ugc-batch-moderator",
    run_id=RUN_ID,
    config={"model_variant": GEMMA_MODEL_VARIANT},
    metadata={...},
    summary={"n_results": len(rows)},
    results=rows,
)
paths = write_v1_bundle(envelope, OUTPUT_DIR)
```

## Tier 4 — audit-script enforcement

Add to `scripts/validate_public_surface.py`:

```python
def check_bundle_envelope_v1(kaggle_dir: Path) -> list[Finding]:
    """Scan each kernel.py for canonical bundle shape compliance."""
    findings = []
    for kp in sorted(kaggle_dir.glob("*/kernel.py")):
        text = kp.read_text(encoding="utf-8")
        if 'schema_version": "duecare.' in text:
            findings.append(Finding(
                path=str(kp),
                rule="bundle_envelope_v1.schema_version",
                detail="custom schema_version string; "
                        "canonical is '1.0'"))
        if '"aggregate":' in text and '"summary":' not in text:
            findings.append(Finding(
                path=str(kp),
                rule="bundle_envelope_v1.aggregate",
                detail="uses 'aggregate' top-level field instead of "
                        "canonical 'summary'"))
        for alt in ('"ingested":', '"proposals":', '"packs_built":'):
            if alt in text and '"results":' not in text:
                findings.append(Finding(
                    path=str(kp),
                    rule="bundle_envelope_v1.results_alt",
                    detail=f"uses {alt} instead of canonical "
                            f"'results':"))
    return findings
```

Add `bundle_envelope_v1` to the audit's check registry. Run
locally before each push:

```
.venv/Scripts/python.exe scripts/validate_public_surface.py
```

## Compatibility timeline

| Date | Milestone |
|---|---|
| 2026-05-12 | This plan committed |
| 2026-05-13 | Tier 1 fixes applied + pushed (A-04, A-19, A-20) |
| 2026-05-14 | Tier 2 fixes applied + pushed (renames, error fields) |
| 2026-05-15 | `duecare.appendix_primitives` module landed + unit-tested |
| 2026-05-16 | Audit check `bundle_envelope_v1` shipped |
| 2026-05-18 | Hackathon submission deadline — everything canonical |
| Post-hackathon | Kernel migrations to use the helper module, one at a time |

## What to do if you find new drift

1. Add a row to `docs/data_primitives.md` § 3 (drift table).
2. Add a fix entry here under the appropriate Tier section with
   a concrete diff snippet.
3. Update `docs/data_surface_inventory.md` § 1 / § 2 to reflect
   the kernel's actual shape (mark the row ⚠).
4. File the kernel.py change with a commit message linking to
   this plan.

**Single rule of thumb:** if a kernel emits JSON and is not on
the canonical path, an entry MUST exist here describing the fix.
No silent drift.

## Status (2026-05-12)

All four tiers landed in `master` on 2026-05-12.

| Tier | Commit | Status | Artifacts |
|---|---|---|---|
| 1 | `c0e6f64` | DONE | A-04 schema_version normalized; A-19 / A-20 RunIDs added |
| 2 | `c0e6f64` | DONE | 4x aggregate -> summary aliases; 3x results[]-rename aliases; 2x error:null defaults; A-11 flatten |
| 3 | `9be6b74` | DONE | `duecare.appendix_primitives` module shipped (0.17.0) + 20 unit tests |
| 4 | `9be6b74` | DONE | `check_bundle_envelope_v1` registered in `scripts/validate_public_surface.py` |

The Tier-3 module exports:

```python
from duecare.appendix_primitives import (
    BundleEnvelope, PerRow, HarnessTrace,
    HarnessGrep, HarnessRag, HarnessTools,
    HarnessOnline, HarnessPersona,
    make_run_id, write_v1_bundle, read_v1_bundle,
    validate_canonical,
)
```

The Tier-4 check (`bundle_envelope_v1`) honors the existing
`audit-allow:drift` inline / above-line marker so a kernel using a
flagged key for a non-envelope purpose can opt out with a one-line
justification. Current example: `kaggle/A-07-bench-and-tune/kernel.py`
uses `"aggregate"` as a phase-result dict key, never a v1.0 envelope
field.

Open follow-up (post-submission): one-at-a-time migration of the 11
fixed kernels from Tier-1+2 legacy-alias rollover state to using
`write_v1_bundle()` directly. The legacy aliases stay in place until
each kernel migrates.
