"""Re-runnable knowledge-surface verification.

Verifies that the major knowledge surfaces of the DueCare harness
parse cleanly and report the expected counts, WITHOUT requiring the
FastAPI / pydantic / numpy stack (which may be broken in the local
venv). Uses Python stdlib only: ast, json, pathlib, re.

Run:
    python scripts/verify_knowledge_surfaces.py

Returns exit code 0 on full pass, non-zero on any AST or JSON error.
"""
from __future__ import annotations

import ast
import json
import pathlib
import re
import sys


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
HARNESS_DIR = REPO_ROOT / "packages/duecare-llm-chat/src/duecare/chat/harness"
HARNESS_PY = HARNESS_DIR / "__init__.py"
# The 2026-07-04 refactor extracted the biggest literals out of the __init__
# monolith into dedicated modules. Each surface is a top-level literal in
# exactly one of these files; parse them all and merge (see the counts section).
HARNESS_SURFACE_MODULES = (
    HARNESS_PY,
    HARNESS_DIR / "_grep_rules.py",          # GREP_RULES
    HARNESS_DIR / "_rag_corpus.py",          # RAG_CORPUS
    HARNESS_DIR / "_multidomain_corpus.py",  # MULTIDOMAIN_CORPUS
)
TEMPLATES_PY = (
    REPO_ROOT / "packages/duecare-llm-chat/src/duecare/chat/templates.py"
)
PERSONAS_JSON = (
    REPO_ROOT
    / "packages/duecare-llm-chat/src/duecare/chat/harness/_personas.json"
)
KAGGLE_KERNELS = [
    REPO_ROOT / "kaggle/01-duecare-exploration-workbench/kernel.py",
    REPO_ROOT / "kaggle/02-live-demo/kernel.py",
    REPO_ROOT / "kaggle/A-00-omni-experiment-workbench/kernel.py",
]


def _count_top_level_assigns(tree: ast.Module) -> dict[str, tuple[str, int]]:
    out: dict[str, tuple[str, int]] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id.isupper():
                    val = node.value
                    if isinstance(val, ast.List):
                        out[tgt.id] = ("list", len(val.elts))
                    elif isinstance(val, ast.Dict):
                        out[tgt.id] = ("dict", len(val.keys))
                    elif isinstance(val, ast.Tuple):
                        out[tgt.id] = ("tuple", len(val.elts))
        elif isinstance(node, ast.AnnAssign):
            if hasattr(node.target, "id"):
                val = node.value
                if isinstance(val, ast.Dict):
                    out[node.target.id] = ("dict", len(val.keys))
                elif isinstance(val, ast.List):
                    out[node.target.id] = ("list", len(val.elts))
    return out


def _template_field_counts(tree: ast.Module) -> list[tuple[str, int, int, str]]:
    """Returns [(template_id, n_fields, n_required, jurisdiction), ...]."""
    rows: list[tuple[str, int, int, str]] = []
    for node in tree.body:
        if not isinstance(node, ast.AnnAssign):
            continue
        if not (hasattr(node.target, "id") and node.target.id == "TEMPLATES_REGISTRY"):
            continue
        if not isinstance(node.value, ast.Dict):
            continue
        for k_node, v_node in zip(node.value.keys, node.value.values):
            if not isinstance(k_node, ast.Constant):
                continue
            tid = k_node.value
            if not isinstance(v_node, ast.Call):
                continue
            n_fields = 0
            n_req = 0
            jurisdiction = "?"
            for kw in v_node.keywords:
                if kw.arg == "fields" and isinstance(kw.value, ast.Tuple):
                    n_fields = len(kw.value.elts)
                    for fc in kw.value.elts:
                        if not isinstance(fc, ast.Call):
                            continue
                        if (
                            len(fc.args) >= 3
                            and isinstance(fc.args[2], ast.Constant)
                            and fc.args[2].value is True
                        ):
                            n_req += 1
                        for fkw in fc.keywords:
                            if (
                                fkw.arg == "required"
                                and isinstance(fkw.value, ast.Constant)
                                and fkw.value.value is True
                            ):
                                n_req += 1
                elif kw.arg == "jurisdiction" and isinstance(kw.value, ast.Constant):
                    jurisdiction = kw.value.value
            rows.append((tid, n_fields, n_req, jurisdiction))
    return rows


def _smoke_render(body_const_name: str, sample: dict) -> tuple[int, int, list[str], str]:
    """Find a body literal in templates.py and substitute sample fields.

    Returns (body_len, rendered_len, unfilled_placeholders, first_line).
    """
    src = TEMPLATES_PY.read_text(encoding="utf-8")
    pattern = re.compile(
        re.escape(body_const_name) + r"\s*=\s*\"\"\"(.*?)\"\"\"",
        flags=re.S,
    )
    m = pattern.search(src)
    if not m:
        raise RuntimeError(f"could not locate {body_const_name} body literal")
    body = m.group(1)
    out = body
    for k, v in sample.items():
        out = out.replace("{{" + k + "}}", str(v))
    unfilled = re.findall(r"\{\{(\w+)\}\}", out)
    first_line = out.splitlines()[0] if out else ""
    return len(body), len(out), unfilled, first_line


def main() -> int:  # noqa: PLR0915
    rc = 0
    print("=== Syntax verification ===")
    for fp in [*HARNESS_SURFACE_MODULES, TEMPLATES_PY, *KAGGLE_KERNELS]:
        if not fp.exists():
            print(f"  {fp.relative_to(REPO_ROOT)}  MISSING")
            rc |= 1
            continue
        try:
            src = fp.read_text(encoding="utf-8")
            ast.parse(src)
            print(
                f"  {str(fp.relative_to(REPO_ROOT)):60s} AST OK "
                f"({src.count(chr(10)) + 1} lines)"
            )
        except Exception as e:  # noqa: BLE001
            print(f"  {fp.relative_to(REPO_ROOT)}  AST FAILED: {e}")
            rc |= 1

    if not PERSONAS_JSON.exists():
        print(f"  {PERSONAS_JSON.relative_to(REPO_ROOT)}  MISSING")
        rc |= 1
    else:
        try:
            personas = json.loads(PERSONAS_JSON.read_text(encoding="utf-8"))
            print(
                f"  {str(PERSONAS_JSON.relative_to(REPO_ROOT)):60s} JSON OK "
                f"(entries={len(personas.get('entries', []))}, "
                f"schema={personas.get('schema', '')})"
            )
        except Exception as e:  # noqa: BLE001
            print(f"  {PERSONAS_JSON.relative_to(REPO_ROOT)}  JSON FAILED: {e}")
            rc |= 1

    print()
    print("=== Knowledge surface counts ===")
    # GREP_RULES / RAG_CORPUS / MULTIDOMAIN_CORPUS were extracted from __init__
    # into their own modules (2026-07-04); the rest still live in __init__.
    # Parse every surface module and merge so a moved literal is still found.
    surfaces: dict[str, tuple[str, int]] = {}
    for fp in HARNESS_SURFACE_MODULES:
        if not fp.exists():
            continue
        surfaces.update(_count_top_level_assigns(ast.parse(fp.read_text(encoding="utf-8"))))
    key_surfaces = [
        "GREP_RULES",
        "RAG_CORPUS",
        "MULTIDOMAIN_CORPUS",
        "CORRIDOR_FEE_CAPS",
        "FEE_CAMOUFLAGE_DICT",
        "NGO_INTAKE",
        "ILO_CONVENTIONS",
        "ILO_INDICATORS",
    ]
    for k in key_surfaces:
        if k in surfaces:
            kind, n = surfaces[k]
            print(f"  {k:24s} {kind:6s} x {n}")
        else:
            print(f"  {k:24s} MISSING")
            rc |= 2

    templates_tree = ast.parse(TEMPLATES_PY.read_text(encoding="utf-8"))
    template_surfaces = _count_top_level_assigns(templates_tree)
    if "TEMPLATES_REGISTRY" in template_surfaces:
        kind, n = template_surfaces["TEMPLATES_REGISTRY"]
        print(f"  {'TEMPLATES_REGISTRY':24s} {kind:6s} x {n}")
    else:
        print(f"  {'TEMPLATES_REGISTRY':24s} MISSING")
        rc |= 2

    personas = json.loads(PERSONAS_JSON.read_text(encoding="utf-8"))
    print(
        f"  {'PERSONAS':24s} list   x {len(personas.get('entries', []))}"
    )

    print()
    print("=== Template detail (id / field count / required count / jurisdiction) ===")
    for tid, n_fields, n_req, jurisdiction in _template_field_counts(templates_tree):
        print(f"  {tid:42s} fields={n_fields:3} required={n_req:3} ({jurisdiction})")

    print()
    print("=== Smoke render test ===")
    sample = {
        "filed_date": "2026-05-22",
        "respondent_name": "(anonymized employer)",
        "respondent_address": "(verify via contacts pack)",
        "respondent_attention": "HR Manager",
        "destination_country_labour_authority": (
            "Hong Kong Labour Department, Employment Agencies "
            "Administration (EAA)"
        ),
        "worker_origin_country_embassy_or_polo": (
            "Philippine Migrant Workers Office Hong Kong"
        ),
        "worker_name": "(anonymized FDH)",
        "worker_nationality": "Filipino",
        "worksite_or_household": "(anonymized household)",
        "passport_prefix": "P3*****",
        "retention_date": "2026-04-15",
        "document_current_location": "in the employer's residence",
        "conditions_imposed": "must work without leave",
        "destination_statute_citation": (
            "HK Cap. 57 Sec. 32 + HK Cap. 57A Reg. 13"
        ),
        "compliance_deadline": "2026-05-27",
        "worker_current_safety_status": (
            "at Bethune House Migrant Women's Refuge"
        ),
        "complainant_name": "(NGO caseworker)",
        "complainant_org": "Mission for Migrant Workers (HK)",
        "complainant_contact": "verify via contacts pack",
    }
    try:
        body_len, rendered_len, unfilled, first_line = _smoke_render(
            "_TEMPLATE_PASSPORT_RETURN_DEMAND_BODY", sample
        )
        print(
            f"  passport_return_demand: body={body_len}c rendered={rendered_len}c "
            f"unfilled={len(unfilled)}"
        )
        if unfilled:
            print(f"    unfilled placeholders: {unfilled}")
            rc |= 4
        else:
            print("    PASS -- all placeholders substituted")
        print(f"  first line: {first_line}")
    except Exception as e:  # noqa: BLE001
        print(f"  smoke render FAILED: {type(e).__name__}: {e}")
        rc |= 4

    print()
    if rc == 0:
        print("ALL VERIFIED -- knowledge surfaces ready for kernel boot.")
    else:
        print(f"VERIFICATION FAILED -- exit code {rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
