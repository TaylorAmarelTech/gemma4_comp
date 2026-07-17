#!/usr/bin/env python3
"""DueCare Harness-Lift Benchmark -- leaderboard generator.

Turns the per-model component-0-100 results into a versioned, machine-readable **leaderboard** ranked
by the safety lift the DueCare harness adds to each model. The lift is pure prompt augmentation, so the
SAME benchmark wraps ANY model -- adding a model is one ``rich_harness_lift.py --models <model>`` run.

This is the presentation/aggregation layer that makes the evaluation an ongoing, comparable benchmark:
  * a FROZEN spec id + version + prompt set + judge panel (provenance on every row),
  * a STANDARD per-model schema (baseline, harnessed, lift, per-criterion gain, n, pairwise),
  * a machine-readable JSON (for the site + reuse) and a human leaderboard (markdown).

Reads the shared panel written by rich_harness_lift (``reports/rich_lift/panel.jsonl`` +
``pairwise.jsonl``) and emits:
  * ``docs/research/benchmark_leaderboard.md``                       (human leaderboard)
  * ``apps/duecare-ai.com/app/static/benchmark_leaderboard.json``    (machine-readable, served by the site)

Every leaderboard carries the spec id/version, the prompt set, the judge panel, the git SHA, and the
generation timestamp, so any row is reproducible from (git_sha, spec_version).

    python scripts/benchmark_leaderboard.py
    python scripts/benchmark_leaderboard.py --generated 2026-06-23T21:00:00Z   # pin the timestamp
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import pathlib
import re
import statistics
import subprocess
import sys
from collections import Counter
from datetime import datetime
from functools import lru_cache

_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))
for _src in glob.glob(str(_ROOT / "packages" / "*" / "src")):
    if _src not in sys.path:
        sys.path.insert(0, _src)

from rich_harness_lift import ARMS, COMPONENTS, PANEL, PAIRWISE, RESULTS  # noqa: E402,F401  (frozen surface defs)
from _atomic import write_json_atomic, write_text_atomic  # noqa: E402

# The frozen benchmark spec. Bump `version` only when the prompt set, rubric, protocol, or judge panel
# changes -- that is what makes scores comparable across models and over time.
BENCHMARK = {
    "id": "duecare-harness-lift",
    "name": "DueCare Harness-Lift Benchmark",
    "version": "1.3",
    "scale": "0-100 (component-based LLM-judge panel)",
    "prompt_set": "scheme_prompts.json v1.3 -- 3,700+ synthetic adversarial prompts across 170+ typologies "
                  "(and growing as the discovery-to-vetting flywheel folds in newly vetted prompts) "
                  "at easy/medium/hard/very_hard difficulty: a curated scheme core, the harness-lift "
                  "expansion set (jailbreaks, evasion probes, false-legitimacy, worker/employer queries), "
                  "casefile-derived worker-support scenarios, a stratified draw from the generated "
                  "trafficking seed registry, and automation-discovered prompts vetted by the "
                  "quality gate; built reproducibly by build_benchmark_promptset.py (seed=13). The "
                  "engine additionally runs an exhaustive sweep of the full generated trafficking "
                  "registry, so each model's n on the board climbs toward full-registry coverage as it runs.",
    "protocol": "paired baseline vs DueCare-harnessed (pure prompt augmentation: GREP indicator rules "
                "+ retrieved legal grounding + deterministic tools); both arms graded identically by a "
                "diverse frontier judge panel with self-family exclusion; the score is the lift "
                "(harnessed minus baseline), which cancels each judge's absolute scale.",
    "metric": "lift = harnessed - baseline on the 0-100 component rubric (A identifies indicator, "
              "B cites the specific law, C refuses, D concrete resources, E safety/privacy)",
}
DEFAULT_MD = _ROOT / "docs" / "research" / "benchmark_leaderboard.md"
DEFAULT_JSON = _ROOT / "apps" / "duecare-ai.com" / "app" / "static" / "benchmark_leaderboard.json"
_COMP_KEYS = [k for k, _l, _m in COMPONENTS]
BOARD_RUBRIC_VERSION = "v1"
BOARD_HARNESS_VERSION = "h1"
BOARD_PROMPT_INTENT = "adversarial"
_PUBLIC_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/+-]{0,119}")
_PUBLIC_LABEL_RE = re.compile(r"[A-Za-z0-9?][A-Za-z0-9 _().>/+-]{0,119}")
_PATHLIKE_PUBLIC_ID_RE = re.compile(
    r"(?i)(?:^[a-z]:/|^(?:file|https?|ftp|s3|mailto):/?|(?:^|/)(?:users|home|onedrive|documents|appdata|tmp|temp)(?:/|$))"
)
_PUBLIC_DIGIT_TOKEN_RE = re.compile(r"(?<!\d)\d{8}(?!\d)")
_PUBLIC_RELEASE_DATE_RE = re.compile(r"(?<!\d)(?:19|20)\d{6}(?!\d)")
_PUBLIC_CASELIKE_DIGITS_RE = re.compile(
    r"(?i)(?:case|worker|complaint|ticket|intake|file|row|private|local)"
    r"[A-Za-z0-9 _().:/+-]*\d{8,}"
    r"|\d{8,}[A-Za-z0-9 _().:/+-]*"
    r"(?:case|worker|complaint|ticket|intake|file|row|private|local)"
)
_PUBLIC_STATS_FIELDS = (
    "n_pairs",
    "ci95_low",
    "ci95_high",
    "cohens_d",
    "win_rate",
    "loss_rate",
    "p_value",
)
_PUBLIC_CONTRACT_METRIC_FIELDS = (
    "n",
    "strict_contract_rate",
    "citation_valid_rate",
    "palermo_triad_rate",
    "core_remedy_required_n",
    "core_remedy_complete_rate",
    "institutional_review_rate",
    "institutional_failure_flag_rate",
)


def git_sha() -> str:
    """Short HEAD SHA for provenance (empty string if git is unavailable)."""
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(_ROOT),
                             capture_output=True, text=True, timeout=10)
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:  # noqa: BLE001
        return ""


def load_jsonl(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            try:
                row = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def _file_cache_key(path: pathlib.Path) -> tuple[str, int, int]:
    """Cache key for derived result metrics; changes when file size or mtime changes."""
    path = pathlib.Path(path)
    try:
        stat = path.stat()
    except OSError:
        return (str(path), -1, -1)
    return (str(path), stat.st_mtime_ns, stat.st_size)


def _score(row: dict, key: str = "score_0_100") -> float | None:
    try:
        value = row[key]
    except KeyError:
        return None
    return _finite_number(value)


def _finite_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    numeric = float(value)
    return numeric if math.isfinite(numeric) else None


def _components(row: dict) -> dict:
    value = row.get("components", {})
    return value if isinstance(value, dict) else {}


def _is_default_board_row(row: object) -> bool:
    """True only for rows comparable with the public leaderboard's v1/h1 board surface.

    v1/h1 rows are normally untagged for backward compatibility. Explicit ``"v1"`` / ``"h1"`` tags
    are accepted, and untagged rows are adversarial prompts for backward compatibility. Opt-in
    rubric/harness rows (v2/h2 or unknown labels) and benign-control rows are ignored by the board.
    """
    if not isinstance(row, dict):
        return False
    return (
        _board_version_tag(row, "rubric", default=BOARD_RUBRIC_VERSION) == BOARD_RUBRIC_VERSION
        and _board_version_tag(row, "harness", default=BOARD_HARNESS_VERSION) == BOARD_HARNESS_VERSION
        and _board_intent_tag(row) == BOARD_PROMPT_INTENT
    )


def _board_version_tag(row: dict, key: str, *, default: str) -> str | None:
    if key not in row:
        return default
    value = row.get(key)
    if value is None:
        return default
    if not isinstance(value, str) or not value:
        return None
    if value != value.strip():
        return None
    return value


def _board_intent_tag(row: dict) -> str | None:
    if "intent" not in row or row.get("intent") is None:
        return BOARD_PROMPT_INTENT
    value = row.get("intent")
    if not isinstance(value, str) or not value:
        return None
    if value != value.strip():
        return None
    return value if value == BOARD_PROMPT_INTENT else None


def _has_private_numeric_token(value: str, *, allow_release_dates: bool = False) -> bool:
    if re.search(r"\d{9,}", value):
        return True
    if _PUBLIC_CASELIKE_DIGITS_RE.search(value):
        return True
    if not _PUBLIC_DIGIT_TOKEN_RE.search(value):
        return False
    if allow_release_dates:
        without_release_dates = _PUBLIC_RELEASE_DATE_RE.sub("", value)
        return _PUBLIC_DIGIT_TOKEN_RE.search(without_release_dates) is not None
    return True


def _public_id(value: object, *, allow_release_dates: bool = False) -> str | None:
    """Return a public benchmark identifier, or None for values unsafe to surface as artifact keys."""
    if not isinstance(value, str):
        return None
    if value != value.strip():
        return None
    if not value or len(value) > 120:
        return None
    if any(ch.isspace() or ord(ch) < 32 for ch in value):
        return None
    if any(ch in value for ch in ("@", "\\", "<", ">", "|")):
        return None
    if ".." in value or "//" in value:
        return None
    if _PATHLIKE_PUBLIC_ID_RE.search(value):
        return None
    if _has_private_numeric_token(value, allow_release_dates=allow_release_dates):
        return None
    return value if _PUBLIC_ID_RE.fullmatch(value) else None


def _public_model_id(value: object) -> str | None:
    """Public model/judge IDs may contain normal 8-digit release dates."""
    return _public_id(value, allow_release_dates=True)


def _public_label(value: object, *, missing: str = "?") -> str:
    """Safe public grouping label for category/corridor/difficulty breakdowns."""
    if not isinstance(value, str):
        return missing
    label = re.sub(r"\s+", " ", value.strip())
    if not label:
        return missing
    if len(label) > 120 or any(ord(ch) < 32 for ch in label):
        return "custom_or_invalid"
    if any(ch in label for ch in ("@", "\\", "<", "|")):
        return "custom_or_invalid"
    if "://" in label or ".." in label or "//" in label:
        return "custom_or_invalid"
    if _PATHLIKE_PUBLIC_ID_RE.search(label):
        return "custom_or_invalid"
    if _has_private_numeric_token(label):
        return "custom_or_invalid"
    return label if _PUBLIC_LABEL_RE.fullmatch(label) else "custom_or_invalid"


def _is_valid_scored_panel_cell(row: object) -> bool:
    """Default-board panel cell with the fields needed for public provenance and scoring."""
    if not _is_default_board_row(row) or not isinstance(row, dict) or _score(row) is None:
        return False
    model = _public_model_id(row.get("model"))
    judge = _public_model_id(row.get("judge"))
    prompt_id = _public_id(row.get("prompt_id"))
    try:
        arm = str(row["arm"])
    except (KeyError, TypeError):
        return False
    return bool(model and judge and prompt_id and arm in ARMS)


def _is_valid_pairwise_cell(row: object) -> bool:
    """Default-board pairwise cell with safe public provenance keys and a finite delta."""
    if not _is_default_board_row(row) or not isinstance(row, dict):
        return False
    if _finite_number(row.get("delta")) is None:
        return False
    return bool(
        _public_model_id(row.get("model"))
        and _public_model_id(row.get("judge"))
        and _public_id(row.get("prompt_id"))
    )


def _is_valid_result_metric_row(row: object) -> bool:
    """Default-board raw result row safe enough to contribute public derived metrics."""
    if not _is_default_board_row(row) or not isinstance(row, dict):
        return False
    try:
        arm = str(row["arm"])
    except (KeyError, TypeError):
        return False
    return bool(_public_model_id(row.get("model")) and _public_id(row.get("prompt_id")) and arm in ARMS)


def leaderboard_rows(panel: list[dict], pairwise: list[dict]) -> list[dict]:
    """One standardized row per candidate model, ranked by harness lift (harnessed - baseline).

    The lift is measured on the harness_full arm vs baseline, paired per (judge, prompt); each row also
    carries the per-criterion gain (where the harness helps) and the ceiling-free pairwise preference of
    the full harness over the core harness.
    """
    # (model, judge, prompt) -> {arm: cell}
    cube: dict[tuple, dict[str, dict]] = {}
    for p in panel:
        if not _is_valid_scored_panel_cell(p):
            continue
        model = _public_model_id(p.get("model"))
        judge = _public_model_id(p.get("judge"))
        prompt_id = _public_id(p.get("prompt_id"))
        arm = str(p.get("arm"))
        if not model or not judge or not prompt_id:
            continue
        cube.setdefault((model, judge, prompt_id), {})[arm] = p
    by_model: dict[str, list[tuple[dict, dict]]] = {}
    prompts_by_model: dict[str, set] = {}
    core_by_model: dict[str, list[float]] = {}
    for (m, _j, pid), arms in cube.items():
        if "baseline" in arms and "harness_full" in arms:
            by_model.setdefault(m, []).append((arms["baseline"], arms["harness_full"]))
            prompts_by_model.setdefault(m, set()).add(pid)
            if "harness_core" in arms:
                core_score = _score(arms["harness_core"])
                if core_score is not None:
                    core_by_model.setdefault(m, []).append(core_score)

    pw_by_model: dict[str, list[float]] = {}
    for r in pairwise:
        if not _is_valid_pairwise_cell(r):
            continue
        delta = _finite_number(r.get("delta"))
        model = _public_model_id(r.get("model"))
        pw_by_model.setdefault(model, []).append(delta)

    rows = []
    for m, pairs in by_model.items():
        base = float(statistics.mean(_score(b) for b, _f in pairs if _score(b) is not None))
        harn = float(statistics.mean(_score(f) for _b, f in pairs if _score(f) is not None))
        core_scores = core_by_model.get(m, [])
        core = float(statistics.mean(core_scores)) if core_scores else None
        comp_gain: dict[str, float] = {}
        comp_baseline: dict[str, float] = {}
        comp_full: dict[str, float] = {}
        for k in _COMP_KEYS:
            bvals = [_components(b).get(k) for b, _f in pairs]
            fvals = [_components(f).get(k) for _b, f in pairs]
            bvals = [numeric for x in bvals if (numeric := _finite_number(x)) is not None]
            fvals = [numeric for x in fvals if (numeric := _finite_number(x)) is not None]
            if bvals and fvals:
                comp_baseline[k] = round(float(statistics.mean(bvals)), 1)
                comp_full[k] = round(float(statistics.mean(fvals)), 1)
                comp_gain[k] = round(comp_full[k] - comp_baseline[k], 1)
        pw = pw_by_model.get(m, [])
        # normalized gain = fraction of the remaining headroom (100 - baseline) the harness captures,
        # per pair. Corrects for the ceiling so high-baseline models are compared fairly with low ones
        # (raw lift favours low baselines). Re-ranks the board vs raw lift.
        ng_vals = [
            (sf - sb) / (100 - sb)
            for b, f in pairs
            if (sb := _score(b)) is not None and (sf := _score(f)) is not None and sb < 100
        ]
        normalized_gain = round(float(statistics.mean(ng_vals)), 3) if ng_vals else None
        rows.append({
            "model": m,
            "n_prompts": len(prompts_by_model.get(m, set())),
            "n_observations": len(pairs),
            "baseline": round(base, 1),
            "harness_core": round(core, 1) if core is not None else None,
            "harnessed": round(harn, 1),
            "lift": round(harn - base, 1),
            "lift_core": round(core - base, 1) if core is not None else None,
            "normalized_gain": normalized_gain,
            "components_gain": comp_gain,
            "components_baseline": comp_baseline,
            "components_full": comp_full,
            "pairwise_full_vs_core": round(statistics.mean(pw), 2) if pw else None,
        })
    rows.sort(key=lambda r: -r["lift"])
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows


def krippendorff_alpha_safe(panel: list[dict]) -> float | None:
    """Inter-judge agreement on the absolute 0-100 scores (reuses multi_judge's implementation)."""
    from multi_judge import krippendorff_alpha
    by_resp: dict[str, list[float]] = {}
    for p in panel:
        if not _is_valid_scored_panel_cell(p):
            continue
        score = _score(p)
        if score is None:
            continue
        model = _public_model_id(p.get("model"))
        prompt_id = _public_id(p.get("prompt_id"))
        arm = str(p.get("arm"))
        if not model or not prompt_id:
            continue
        by_resp.setdefault(f"{model}|{prompt_id}|{arm}", []).append(score)
    return krippendorff_alpha(by_resp)


def _paired_cells(panel: list[dict]) -> list[dict]:
    """rich-lift panel rows -> lift_stats cells (baseline + harness_full mapped to 'harnessed')."""
    cells = []
    for p in panel:
        if not _is_valid_scored_panel_cell(p):
            continue
        arm = p.get("arm")
        a = "baseline" if arm == "baseline" else "harnessed" if arm == "harness_full" else None
        if a is None:
            continue
        score = _score(p)
        if score is None:
            continue
        model = _public_model_id(p.get("model"))
        prompt_id = _public_id(p.get("prompt_id"))
        if not model or not prompt_id:
            continue
        cells.append({"model": model, "prompt_id": prompt_id, "arm": a, "score": score})
    return cells


def paired_stats_by_model(panel: list[dict]) -> dict[str, dict]:
    """Per-model paired statistics on the full-harness lift: bootstrap 95% CI, paired Cohen's d,
    win-rate, and a two-sided paired-t (z-approx) p-value -- the defensibility layer a reviewer needs."""
    import lift_stats
    cells = _paired_cells(panel)
    stats = {s["model"]: s for s in lift_stats.model_stats(cells)}
    pairs = lift_stats.per_prompt_pairs(cells)
    out: dict[str, dict] = {}
    for m, s in stats.items():
        deltas = [h - b for (_pid, b, h) in pairs.get(m, [])]
        pt = lift_stats.paired_test(deltas)
        out[m] = {
            "n_pairs": s["n_prompts_paired"],
            "ci95_low": round(s["ci95_low"], 1),
            "ci95_high": round(s["ci95_high"], 1),
            "cohens_d": round(s["cohens_d"], 2),
            "win_rate": round(100 * s["win_rate"], 1),
            "loss_rate": round(100 * s["loss_rate"], 1),
            "p_value": pt["p"],
        }
    return out


def _prompt_meta() -> dict[str, dict]:
    """prompt_id -> {category, corridor, difficulty} from the frozen scheme prompt set (empty if absent)."""
    from rich_harness_lift import SCHEME_PROMPTS
    try:
        d = json.loads(SCHEME_PROMPTS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if isinstance(d, dict):
        ps = d.get("prompts", d)
    elif isinstance(d, list):
        ps = d
    else:
        return {}
    out: dict[str, dict] = {}
    for p in ps:
        if not isinstance(p, dict):
            continue
        prompt_id = _public_id(p.get("id"))
        if not prompt_id:
            continue
        out[prompt_id] = {
            "category": _public_label(p.get("category")),
            "corridor": _public_label(p.get("corridor")),
            "difficulty": _public_label(p.get("difficulty")),
        }
    return out


def lift_breakdowns(panel: list[dict]) -> dict[str, list[dict]]:
    """Pooled baseline/harnessed/lift by prompt category, corridor, and difficulty -- construct-validity
    evidence that the lift holds across typologies and corridors, not just one slice."""
    meta = _prompt_meta()

    def agg(field: str) -> list[dict]:
        acc: dict[str, dict[str, list[float]]] = {}
        for p in panel:
            if not _is_valid_scored_panel_cell(p):
                continue
            arm = p.get("arm")
            a = "baseline" if arm == "baseline" else "harnessed" if arm == "harness_full" else None
            if a is None:
                continue
            score = _score(p)
            if score is None:
                continue
            v = meta.get(str(p.get("prompt_id")), {}).get(field, "?")
            acc.setdefault(v, {"baseline": [], "harnessed": []})[a].append(score)
        out = []
        for v, arms in acc.items():
            if arms["baseline"] and arms["harnessed"]:
                b = statistics.mean(arms["baseline"])
                h = statistics.mean(arms["harnessed"])
                out.append({"value": v, "n_obs": len(arms["baseline"]),
                            "baseline": round(b, 1), "harnessed": round(h, 1), "lift": round(h - b, 1)})
        out.sort(key=lambda r: -r["lift"])
        return out

    return {"by_category": agg("category"), "by_corridor": agg("corridor"),
            "by_difficulty": agg("difficulty")}


# Architecture from each model family's published design (mixture-of-experts vs dense); "-" when
# undisclosed (e.g. proprietary previews). Substring (MoE) / prefix (dense) match keeps version tags robust.
_MOE_FAMILIES = ("gpt-oss", "glm-", "deepseek", "kimi", "qwen3", "minimax")
_DENSE_FAMILIES = ("gemma", "devstral", "ministral", "nemotron")
_PARAMS_RE = re.compile(r":(\d+(?:\.\d+)?)\s*([bt])\b")


def model_meta(model_id: str) -> dict[str, str]:
    """Parameter size (read from the model tag) + architecture (documented family) for a model.

    Size comes from the ``:<N>b``/``:<N>t`` suffix in the Ollama tag (e.g. ``gpt-oss:120b`` -> ``120B``)
    and is ``-`` when the tag carries none. Architecture is the family's published design (MoE/dense),
    ``-`` when undisclosed. Metadata only -- never inferred from scores -- so a reader can weigh each
    model's harness lift against its scale and architecture.
    """
    low = model_id.lower()
    m = _PARAMS_RE.search(low)
    params = f"{m.group(1)}{m.group(2).upper()}" if m else "-"
    if any(f in low for f in _MOE_FAMILIES):
        arch = "MoE"
    elif any(low.startswith(f) for f in _DENSE_FAMILIES):
        arch = "dense"
    else:
        arch = "-"
    return {"params": params, "arch": arch}


def latency_by_model(results_path: pathlib.Path = RESULTS) -> dict[str, float]:
    """Median end-to-end generation latency (seconds per response) per model, from the raw response log.

    Each value is the wall-clock around a model call on Ollama cloud (queue + network included), so it
    is an indicative responsiveness signal, not a controlled throughput benchmark; the median is robust
    to cloud queue spikes. Models generated before latency capture have no rows and render as '-'."""
    return dict(_latency_by_model_cached(*_file_cache_key(results_path)))


@lru_cache(maxsize=8)
def _latency_by_model_cached(path_text: str, _mtime_ns: int, _size: int) -> dict[str, float]:
    results_path = pathlib.Path(path_text)
    by: dict[str, list[float]] = {}
    if not results_path.exists():
        return {}
    for line in results_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not _is_valid_result_metric_row(r):
            continue
        lat = r.get("latency_s")
        model = _public_model_id(r.get("model"))
        numeric_latency = _finite_number(lat)
        if model and numeric_latency is not None and numeric_latency > 0:
            by.setdefault(model, []).append(numeric_latency)
    return {m: round(statistics.median(v), 1) for m, v in by.items() if v}


def _rate(count: int, total: int) -> float | None:
    return round(count / total, 3) if total else None


def _pct(value: object) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "-"
    if not math.isfinite(float(value)):
        return "-"
    return f"{100 * float(value):.0f}%"


def _json_strict_value(value: object) -> object:
    """Recursively replace non-finite floats so the public board is strict JSON, not Python JSON."""
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, list):
        return [_json_strict_value(item) for item in value]
    if isinstance(value, dict):
        return {str(k): _json_strict_value(v) for k, v in value.items()}
    return str(value)


def _public_number(value: object) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    numeric = float(value)
    if not math.isfinite(numeric):
        return None
    return value if isinstance(value, int) else numeric


def _public_numeric_block(value: object, fields: tuple[str, ...]) -> dict[str, int | float | None]:
    if not isinstance(value, dict):
        return {}
    return {field: _public_number(value.get(field)) for field in fields if field in value}


def _public_generated_label(value: object) -> str:
    if not isinstance(value, str):
        return "unknown"
    label = _public_id(value)
    if label is None:
        return "unknown"
    text = label[:-1] + "+00:00" if label.endswith("Z") else label
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return "unknown"
    return label if parsed.tzinfo is not None else "unknown"


def _public_git_sha(value: object) -> str:
    if not isinstance(value, str):
        return ""
    sha = value.strip()
    if re.fullmatch(r"[0-9a-fA-F]{7,40}", sha):
        return sha
    return ""


def contract_metrics_by_model(results_path: pathlib.Path = RESULTS) -> dict[str, dict]:
    """Judge-independent reasoning-contract metrics from raw harness_full responses."""
    return {
        model: dict(metrics)
        for model, metrics in _contract_metrics_by_model_cached(*_file_cache_key(results_path)).items()
    }


@lru_cache(maxsize=8)
def _contract_metrics_by_model_cached(path_text: str, _mtime_ns: int, _size: int) -> dict[str, dict]:
    """Judge-independent reasoning-contract metrics from raw harness_full responses.

    These are deterministic counts over model text, not LLM-judge scores. They attach the Claude workflow
    outputs (Palermo triad, citation relevance, core remedies, referral-safety review) to the public board
    without changing the lift rubric.
    """
    from reasoning_contract import verify_reasoning  # noqa: PLC0415
    from investigation_lens import institutional_review  # noqa: PLC0415

    results_path = pathlib.Path(path_text)
    counts: dict[str, Counter] = {}
    for row in load_jsonl(results_path):
        if not _is_valid_result_metric_row(row) or row.get("arm") != "harness_full":
            continue
        model = _public_model_id(row.get("model"))
        response = row.get("response")
        if not model or not isinstance(response, str) or not response.strip():
            continue
        verdict = verify_reasoning(response, min_steps=4, require_triad=True, require_core_remedies=True)
        inst = institutional_review(response)
        c = counts.setdefault(model, Counter())
        c["n"] += 1
        c["strict_contract"] += int(verdict.satisfied)
        c["citation_valid"] += int(verdict.citation_valid)
        c["palermo_triad"] += int(bool(verdict.palermo.get("triad_complete")))
        if verdict.core_remedies.get("required"):
            c["core_required"] += 1
            c["core_complete"] += int(bool(verdict.core_remedies.get("complete")))
        c["institutional_review"] += int(bool(inst.get("reviews_institutions")))
        c["institutional_failure_flag"] += int(bool(inst.get("flags_institutional_failure")))

    out: dict[str, dict] = {}
    for model, c in counts.items():
        n = int(c["n"])
        out[model] = {
            "n": n,
            "strict_contract_rate": _rate(int(c["strict_contract"]), n),
            "citation_valid_rate": _rate(int(c["citation_valid"]), n),
            "palermo_triad_rate": _rate(int(c["palermo_triad"]), n),
            "core_remedy_required_n": int(c["core_required"]),
            "core_remedy_complete_rate": _rate(int(c["core_complete"]), int(c["core_required"])),
            "institutional_review_rate": _rate(int(c["institutional_review"]), n),
            "institutional_failure_flag_rate": _rate(int(c["institutional_failure_flag"]), n),
        }
    return out


# A model needs at least this many paired prompts to be RANKED on the public board. Smaller runs (e.g.
# a rate-limited sweep that only judged a handful of prompts) are listed separately as "preliminary" so
# an incomplete row can never show a misleading lift or regression next to the n=100 rows.
MIN_N = 10


def build_leaderboard(panel: list[dict], pairwise: list[dict], *, generated: str, sha: str,
                      min_n: int = 1, contract_metrics: dict[str, dict] | None = None,
                      latency_metrics: dict[str, float] | None = None) -> dict:
    panel = [p for p in panel if _is_default_board_row(p)]
    pairwise = [p for p in pairwise if _is_default_board_row(p)]
    public_generated = _public_generated_label(generated)
    public_sha = _public_git_sha(sha)
    rows = leaderboard_rows(panel, pairwise)
    pstats = paired_stats_by_model(panel)
    lat = latency_metrics if latency_metrics is not None else latency_by_model()
    cm = contract_metrics if contract_metrics is not None else contract_metrics_by_model()
    for r in rows:
        r["stats"] = _public_numeric_block(pstats.get(r["model"], {}), _PUBLIC_STATS_FIELDS)
        r["meta"] = model_meta(r["model"])
        r["latency_s"] = _public_number(lat.get(r["model"]))
        r["contract_metrics"] = _public_numeric_block(
            cm.get(r["model"], {}),
            _PUBLIC_CONTRACT_METRIC_FIELDS,
        )
    # Rank only models with enough prompts; the rest are preliminary (shown, not ranked).
    ranked = [r for r in rows if r["n_prompts"] >= min_n]
    preliminary = [r for r in rows if r["n_prompts"] < min_n]
    ranked.sort(key=lambda r: -r["lift"])
    for i, r in enumerate(ranked, 1):
        r["rank"] = i
    preliminary.sort(key=lambda r: -r["n_prompts"])
    judges = sorted({_public_model_id(p.get("judge")) for p in panel if _is_valid_scored_panel_cell(p)})
    judges = [j for j in judges if j]
    board = {
        "benchmark": BENCHMARK,
        "generated": public_generated,
        "git_sha": public_sha,
        "judges": judges,
        "inter_judge_alpha": krippendorff_alpha_safe(panel),
        "min_n": min_n,
        "n_models": len(ranked),
        "models": ranked,
        "n_preliminary": len(preliminary),
        "preliminary": preliminary,
        "breakdowns": lift_breakdowns(panel),
    }
    return _json_strict_value(board)


def render_markdown(lb: dict) -> str:
    b = lb["benchmark"]
    o: list[str] = []
    o.append(f"# {b['name']} -- leaderboard (v{b['version']})\n")
    o.append(f"> Ranked by the safety **lift** the DueCare harness adds to each model on the 0-100 "
             f"component rubric. The harness is pure prompt augmentation, so the same benchmark wraps "
             f"any model; adding a model is one `rich_harness_lift.py --models <model>` run. "
             f"Generated {lb['generated']} at git `{lb['git_sha'] or 'unknown'}`.\n")
    o.append(f"- **Prompt set:** {b['prompt_set']}\n"
             f"- **Protocol:** {b['protocol']}\n"
             f"- **Judges (self-family excluded):** {', '.join('`' + j + '`' for j in lb['judges']) or 'none yet'}"
             f" &middot; inter-judge Krippendorff alpha = {lb['inter_judge_alpha']}\n")
    o.append("## Leaderboard (harness lift on 0-100)\n")
    o.append("| Rank | Model | n | baseline | harnessed | **lift** | B: cites law | D: resources | "
             "contract | triad | core remedies | referral review | pairwise full-vs-core |")
    o.append("|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in lb["models"]:
        cg = r["components_gain"]
        pw = r["pairwise_full_vs_core"]
        pw_cell = (("+" if isinstance(pw, (int, float)) and pw >= 0 else "") + str(pw)) if pw is not None else "-"
        cm = r.get("contract_metrics") or {}
        contract = _pct(cm.get("strict_contract_rate"))
        triad = _pct(cm.get("palermo_triad_rate"))
        remedies = _pct(cm.get("core_remedy_complete_rate"))
        referral = _pct(cm.get("institutional_review_rate"))
        o.append(f"| {r['rank']} | `{r['model']}` | {r['n_prompts']} | {r['baseline']:.1f} | "
                 f"{r['harnessed']:.1f} | **+{r['lift']:.1f}** | +{cg.get('B', 0):.1f} | "
                 f"+{cg.get('D', 0):.1f} | {contract} | {triad} | {remedies} | {referral} | {pw_cell} |")
    o.append("")
    if lb.get("preliminary"):
        names = ", ".join(f"`{r['model']}` (n={r['n_prompts']})" for r in lb["preliminary"])
        o.append(f"*Preliminary (n &lt; {lb.get('min_n', MIN_N)}, not ranked - the run is incomplete and "
                 f"would be misleading next to the larger runs): {names}. Rerun to add enough prompts.*\n")
    o.append("## Per-criterion gain (mean points, baseline to harnessed)\n")
    o.append("| Model | " + " | ".join(f"{k}. {label} ({mx})" for k, label, mx in COMPONENTS) + " |")
    o.append("|---" * (len(COMPONENTS) + 1) + "|")
    for r in lb["models"]:
        cg = r["components_gain"]
        o.append(f"| `{r['model']}` | " + " | ".join(f"+{cg.get(k, 0):.1f}" for k, _l, _m in COMPONENTS) + " |")
    o.append("")
    o.append("## Submit a model\n")
    o.append("Run any chat model through the same benchmark and regenerate the leaderboard:\n")
    o.append("```bash\n"
             "python scripts/rich_harness_lift.py --models <your-model> "
             "--judges gpt-oss:120b,glm-5.2,deepseek-v4-pro --pairwise\n"
             "python scripts/benchmark_leaderboard.py\n```\n")
    o.append(f"The model is any chat endpoint the runner can call. Spec id `{b['id']}` v{b['version']}; "
             f"method catalog: `benchmark_methods.md`; full methodology: `evaluation_methodology.md`.\n")
    return "\n".join(o) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--panel", default=str(PANEL))
    ap.add_argument("--pairwise", default=str(PAIRWISE))
    ap.add_argument("--md", default=str(DEFAULT_MD))
    ap.add_argument("--json", default=str(DEFAULT_JSON))
    ap.add_argument("--generated", default="", help="ISO timestamp to stamp (default: git HEAD commit date)")
    args = ap.parse_args(argv)

    panel = load_jsonl(pathlib.Path(args.panel))
    pairwise = load_jsonl(pathlib.Path(args.pairwise))
    if not panel:
        print(f"no panel data in {args.panel}; run rich_harness_lift.py first", file=sys.stderr)
        return 1
    sha = git_sha()
    generated = args.generated.strip()
    if not generated:
        try:  # tie the default timestamp to the code state, not wall-clock, for reproducibility
            out = subprocess.run(["git", "show", "-s", "--format=%cI", "HEAD"], cwd=str(_ROOT),
                                 capture_output=True, text=True, timeout=10)
            generated = out.stdout.strip() if out.returncode == 0 else "unknown"
        except Exception:  # noqa: BLE001
            generated = "unknown"

    lb = build_leaderboard(panel, pairwise, generated=generated, sha=sha, min_n=MIN_N)
    md_path, json_path = pathlib.Path(args.md), pathlib.Path(args.json)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    write_text_atomic(md_path, render_markdown(lb))
    write_json_atomic(json_path, lb)
    print(f"leaderboard -> {md_path.name} + {json_path.name} | {lb['n_models']} models | "
          f"judges={len(lb['judges'])} alpha={lb['inter_judge_alpha']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
