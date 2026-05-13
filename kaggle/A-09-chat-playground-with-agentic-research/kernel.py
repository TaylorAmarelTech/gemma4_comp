# <!-- duecare:kernel-intro -->
# DueCare — PII synthetic data generator (composite intake + gold redaction plans)
# Appendix notebook #A09 of 24 in the DueCare submission.
#
# Generates 100% SYNTHETIC composite worker-intake notes (fake names,
# passports, phones, addresses, employers) with paired gold redaction
# plans. Output JSONL ready for the A-11 PrivacyRedactor LoRA trainer.
# No real worker PII ever flows through this kernel.
#
# What to look for after Run All:
#   - Open the printed cloudflared URL; summary + download links.
#   - Per-scenario coverage shown (recruitment fraud, fee bondage,
#     passport retention, salary withholding, etc.).
#   - JSONL + bundle.zip + metadata.json land in /kaggle/working/.
#
# Demo path: Run All -> bundle.zip downloads -> attach to A-11 for
# the PrivacyRedactor adapter training.
#
# Full README + cross-kernel index: see the README in this folder.

"""
============================================================================
  DUECARE A-09 CHAT PLAYGROUND WITH AGENTIC RESEARCH -- Kaggle notebook
============================================================================

  Per Taylor's 2026-05-11 experiment-ladder spec, A-10 produces
  synthetic training material for the PrivacyRedactor adapter that
  A-11 trains. Two paired tracks per composite:

    composite_text   the synthetic intake note (with fake PII)
    redacted_text    the expected redacted output the model should
                       produce
    redactions[]     spans + labels marking exactly what was removed

  All PII values are FAKE -- generated from Faker-style template
  tables. No real worker name, passport, phone, or address ever flows
  through this kernel. The Anonymizer agent (per
  .claude/rules/10_safety_gate.md) is enforced by construction:
  every PII slot is a template fill from a constrained pool.

  Output: v1.0 bundle to /kaggle/working
    <run_id>_pii_composite.json    full payload (composites + gold)
    <run_id>_pii_composite.jsonl   streaming variant
    <run_id>_pii_gold.jsonl        gold redaction plans only
    <run_id>_metadata.json         config + summary
    <run_id>_bundle.zip            manifest + all of the above

  Run-ID format: a10_pii_synth_{iso_ts}

  Requirements:
    - GPU: NOT required (template-based; zero model load)
    - Internet: ON (GitHub package install only; generation is offline)
    - Wheels dataset: none (GitHub-only install per 2026-05-11 policy)

  Expected runtime: ~30s install + ~5s per 100 composites generated.

  Built with Google's Gemma 4. Used in accordance with the Gemma Terms of Use.
============================================================================
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
import subprocess
import sys
import threading
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


# ===========================================================================
# CONFIG
# ===========================================================================
PORT = 8080
TUNNEL = "cloudflared"
OUTPUT_DIR = Path("/kaggle/working")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

N_COMPOSITES = int(os.environ.get("DUECARE_N_PII_COMPOSITES", "200"))
RANDOM_SEED = int(os.environ.get("DUECARE_PII_SEED", "20260511"))


# ===========================================================================
# PHASE 1 -- install DueCare from GitHub (no Kaggle wheel datasets)
# ===========================================================================
DUECARE_VERSION    = "0.1.0"
DUECARE_REPO       = "TaylorAmarelTech/gemma4_comp"
DUECARE_COMMIT_SHA = "main"
DUECARE_PACKAGES   = ["duecare-llm-chat"]


def install_duecare_from_github() -> bool:
    print("=" * 76)
    print("[install] DueCare packages from GitHub (no Kaggle wheel datasets)")
    print("=" * 76)
    base_url = (f"https://github.com/{DUECARE_REPO}/releases/download/"
                f"v{DUECARE_VERSION}")
    success = 0
    for i, pkg in enumerate(DUECARE_PACKAGES, 1):
        wheel_name = (f"{pkg.replace('-', '_')}-{DUECARE_VERSION}"
                      f"-py3-none-any.whl")
        url = f"{base_url}/{wheel_name}"
        print(f"  > [{i}/{len(DUECARE_PACKAGES)}] release wheel: {wheel_name}")
        cmd = [sys.executable, "-m", "pip", "install", "--no-input",
               "--disable-pip-version-check", "--timeout=60", url]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        if proc.returncode == 0:
            success += 1
            print(f"  + installed {pkg} from release v{DUECARE_VERSION}")
        else:
            tail = (proc.stderr or "")[-200:]
            if "404" in tail or "Not Found" in tail:
                print(f"  - release wheel not found, falling back to source")
                break
            print(f"  - {pkg} release wheel failed: {tail}")
    if success == len(DUECARE_PACKAGES):
        for mod in list(sys.modules):
            if mod == "duecare" or mod.startswith("duecare."):
                del sys.modules[mod]
        return True
    git_pkgs = [
        f"git+https://github.com/{DUECARE_REPO}.git@{DUECARE_COMMIT_SHA}"
        f"#subdirectory=packages/{p}"
        for p in DUECARE_PACKAGES
    ]
    print(f"  > source install @ {DUECARE_COMMIT_SHA}")
    cmd = [sys.executable, "-m", "pip", "install", "--no-input",
           "--disable-pip-version-check", "--timeout=300", *git_pkgs]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=420)
    if proc.returncode == 0:
        for mod in list(sys.modules):
            if mod == "duecare" or mod.startswith("duecare."):
                del sys.modules[mod]
        print(f"  + source install ok @ {DUECARE_COMMIT_SHA}")
        return True
    raise SystemExit(
        f"DueCare GitHub install failed: {(proc.stderr or '')[-300:]}")


print("\n" + "=" * 76)
print("[1/4] installing DueCare from GitHub")
print("=" * 76)
install_duecare_from_github()
subprocess.run([sys.executable, "-m", "pip", "install", "--quiet",
                  "--no-input", "--disable-pip-version-check",
                  "fastapi>=0.115.0", "uvicorn>=0.30.0",
                  "python-multipart>=0.0.9"],
                  capture_output=True, text=True)


try:
    from duecare.chat._dc_log import dc_log, set_kernel_id
    set_kernel_id("a-10-pii-synth-data-generator")
except Exception:
    def dc_log(*a, **kw): return None  # type: ignore[no-redef]
    def set_kernel_id(*a, **kw): return None  # type: ignore[no-redef]


# ===========================================================================
# 2. SYNTHETIC PII POOLS (template values; never real worker data)
# ===========================================================================
_FIRST_NAMES_PH = ["Maria", "Ana", "Rosario", "Liza", "Jocelyn",
                    "Catherine", "Genevieve", "Marisol", "Cristina",
                    "Imelda"]
_FIRST_NAMES_NP = ["Sita", "Bishnu", "Kamala", "Sunita", "Saraswati",
                    "Laxmi", "Maya", "Parbati", "Ramila", "Ganga"]
_FIRST_NAMES_BD = ["Rahima", "Sultana", "Shahnaz", "Nasreen", "Salma",
                    "Rokeya", "Khaleda", "Jahanara", "Hosne", "Marium"]
_FIRST_NAMES_ID = ["Siti", "Ratna", "Endang", "Tuti", "Wati",
                    "Yanti", "Suryani", "Rini", "Lestari", "Indah"]

_LAST_NAMES_PH = ["Santos", "Cruz", "Bautista", "Reyes", "Garcia",
                   "Mendoza", "Ramirez", "Diaz", "Castro", "Aquino"]
_LAST_NAMES_NP = ["Tamang", "Gurung", "Sherpa", "Magar", "Rai",
                   "Limbu", "Khadka", "Adhikari", "Pokharel", "Bhandari"]
_LAST_NAMES_BD = ["Begum", "Akhter", "Khatun", "Rahman", "Hossain",
                   "Islam", "Ahmed", "Sultana", "Khanam", "Chowdhury"]
_LAST_NAMES_ID = ["Wati", "Sari", "Lestari", "Rahayu", "Putri",
                   "Setiawan", "Pratiwi", "Anggraini", "Hasanah", "Maharani"]

_CORRIDORS = {
    "PH-HK":   {"first": _FIRST_NAMES_PH, "last": _LAST_NAMES_PH,
                  "origin": "Manila", "dest": "Hong Kong",
                  "phone_cc": "+63",  "passport_prefix": "EB"},
    "PH-UAE":  {"first": _FIRST_NAMES_PH, "last": _LAST_NAMES_PH,
                  "origin": "Cebu",   "dest": "Dubai",
                  "phone_cc": "+63",  "passport_prefix": "EC"},
    "NP-Gulf": {"first": _FIRST_NAMES_NP, "last": _LAST_NAMES_NP,
                  "origin": "Kathmandu", "dest": "Doha",
                  "phone_cc": "+977", "passport_prefix": "PA"},
    "BD-Gulf": {"first": _FIRST_NAMES_BD, "last": _LAST_NAMES_BD,
                  "origin": "Dhaka",  "dest": "Riyadh",
                  "phone_cc": "+880", "passport_prefix": "BX"},
    "ID-HK":   {"first": _FIRST_NAMES_ID, "last": _LAST_NAMES_ID,
                  "origin": "Surabaya", "dest": "Hong Kong",
                  "phone_cc": "+62",  "passport_prefix": "AC"},
}

_RECRUITER_NAMES = [
    "Bright Horizon Manpower Services Inc.",
    "Pacific Path Workforce Solutions",
    "Gulf Bridge Employment Co.",
    "Sunrise Domestic Placement Agency",
    "Star Cross Recruitment Pte Ltd",
    "Trans-Asia Career Services",
    "Crescent Moon Manpower Agency",
    "Eastern Light Personnel Co.",
    "Golden Gate Workforce Bureau",
    "New Hope Employment Solutions",
]
_EMPLOYER_NAMES = [
    "Sterling House Services",
    "Royal Family Estate",
    "Madame Wong Household",
    "Al Rashid Family",
    "Bin Saeed Domestic",
    "Chen Household Group",
    "Khaled Family Estate",
    "Lim Residence",
    "Mansour Household",
    "Tan Family Service",
]

_DEST_STREETS = {
    "Hong Kong": ["Nathan Road", "Hennessy Avenue", "Queen's Way",
                    "King's Lane", "Central Plaza Road"],
    "Dubai":     ["Sheikh Zayed Road", "Al Wasl Lane", "Marina Drive",
                    "Jumeirah Beach Road", "Garhoud Avenue"],
    "Doha":      ["Corniche Promenade", "Al Sadd Street",
                    "Education City Boulevard", "West Bay Lane",
                    "Pearl Marina"],
    "Riyadh":    ["King Fahd Road", "Olaya Street", "Tahlia Avenue",
                    "Al Malaz Lane", "Diplomatic Quarter"],
}


def _synth_value(rnd: random.Random, kind: str, corridor: dict) -> str:
    if kind == "FIRST_NAME":
        return rnd.choice(corridor["first"])
    if kind == "LAST_NAME":
        return rnd.choice(corridor["last"])
    if kind == "FULL_NAME" or kind == "NAME":
        return f"{rnd.choice(corridor['first'])} {rnd.choice(corridor['last'])}"
    if kind == "PASSPORT":
        return f"{corridor['passport_prefix']}{rnd.randint(1000000, 9999999)}"
    if kind == "PHONE":
        digits = rnd.randint(100000000, 999999999)
        return f"{corridor['phone_cc']}{digits}"
    if kind == "EMAIL":
        first = rnd.choice(corridor["first"]).lower()
        last = rnd.choice(corridor["last"]).lower()
        domain = rnd.choice(["gmail.com", "yahoo.com", "outlook.com",
                              "hotmail.com"])
        return f"{first}.{last}{rnd.randint(11, 99)}@{domain}"
    if kind == "ADDRESS":
        street_pool = _DEST_STREETS.get(corridor["dest"],
                                          ["Central Avenue"])
        return (f"{rnd.randint(1, 250)} {rnd.choice(street_pool)}, "
                f"{corridor['dest']}")
    if kind == "RECRUITER":
        return rnd.choice(_RECRUITER_NAMES)
    if kind == "EMPLOYER":
        return rnd.choice(_EMPLOYER_NAMES)
    if kind == "DOB":
        return (f"{rnd.randint(1985, 2002):04d}-"
                f"{rnd.randint(1, 12):02d}-{rnd.randint(1, 28):02d}")
    if kind == "AMOUNT_USD":
        return f"USD {rnd.randint(800, 12000)}"
    return f"<{kind}>"


# ===========================================================================
# 3. SCENARIO TEMPLATES (10 corridors-aware intake-note shapes)
# ===========================================================================
_SCENARIOS = [
    {
        "id": "recruitment_fee_overcharge",
        "category": "fee_bondage",
        "template": (
            "My name is {NAME} and I came from {ORIGIN} to {DEST}. "
            "I work as a domestic helper for {EMPLOYER}. The recruiter "
            "{RECRUITER} took {AMOUNT_USD} in fees -- way more than what "
            "the law allows. They took my passport ({PASSPORT}) too. "
            "If you need to call me, my number is {PHONE}, but my employer "
            "checks. Email me at {EMAIL} instead. I live at {ADDRESS}."
        ),
    },
    {
        "id": "passport_confiscation",
        "category": "document_retention",
        "template": (
            "I am {NAME}, born {DOB}. My passport number is {PASSPORT}. "
            "When I arrived from {ORIGIN}, my employer {EMPLOYER} took "
            "the passport on day one and won't return it. The recruiter "
            "({RECRUITER}) said this is normal. My phone is {PHONE} "
            "but I can only answer at night."
        ),
    },
    {
        "id": "salary_withholding",
        "category": "wage_theft",
        "template": (
            "Hi, I'm {NAME}. I have been working for {EMPLOYER} in {DEST} "
            "for 8 months. They have not paid me a single salary -- they "
            "say the {AMOUNT_USD} I owe the recruiter {RECRUITER} comes "
            "out first. My passport ({PASSPORT}) is with them. Please "
            "contact me at {EMAIL} or {PHONE} only when safe."
        ),
    },
    {
        "id": "isolation_and_movement",
        "category": "isolation",
        "template": (
            "{NAME} here. I live at {ADDRESS} working for {EMPLOYER}. "
            "I am not allowed to leave the building. My phone {PHONE} is "
            "monitored; the only safe way is email at {EMAIL}. Recruiter "
            "{RECRUITER} arranged everything from {ORIGIN}. They took "
            "the passport ({PASSPORT}) when I landed in {DEST}."
        ),
    },
    {
        "id": "contract_substitution",
        "category": "contract_fraud",
        "template": (
            "My name is {NAME}, born {DOB}. The contract I signed in "
            "{ORIGIN} promised {AMOUNT_USD} per month working in an "
            "office. When I arrived in {DEST}, the employer {EMPLOYER} "
            "made me sign a different contract for domestic work, half "
            "the salary. Recruiter {RECRUITER} disappeared. My passport "
            "is {PASSPORT}. Reach me at {PHONE} between 9-10 pm only."
        ),
    },
    {
        "id": "physical_abuse_report",
        "category": "abuse",
        "template": (
            "I am {NAME}, working for {EMPLOYER} at {ADDRESS}. The "
            "madame hits me when I am slow. I came from {ORIGIN}. The "
            "recruiter was {RECRUITER}. Passport {PASSPORT} is locked "
            "in the safe. My family in {ORIGIN} can be reached at "
            "{PHONE}; please don't tell my employer you talked to me. "
            "Email is safer: {EMAIL}."
        ),
    },
    {
        "id": "deceptive_recruitment_offer",
        "category": "recruitment_fraud",
        "template": (
            "{NAME} from {ORIGIN}. The agency {RECRUITER} promised me a "
            "shop assistant job in {DEST}. They asked for {AMOUNT_USD} "
            "and my passport ({PASSPORT}) for 'processing'. Now they "
            "won't return either. My phone is {PHONE}. I haven't even "
            "left {ORIGIN} yet -- please advise."
        ),
    },
    {
        "id": "debt_bondage_recurring",
        "category": "debt_bondage",
        "template": (
            "Name: {NAME}. Passport: {PASSPORT}. Born {DOB}. "
            "Recruiter {RECRUITER} loaned me {AMOUNT_USD} for the trip "
            "from {ORIGIN} to {DEST}. The interest doubles every month. "
            "Employer {EMPLOYER} deducts everything from my salary so I "
            "have nothing. Address: {ADDRESS}. Phone: {PHONE}. "
            "Email: {EMAIL}."
        ),
    },
    {
        "id": "sexual_harassment_disclosure",
        "category": "harassment",
        "template": (
            "I'm {NAME} working for {EMPLOYER} in {DEST}. The son keeps "
            "coming into my room at night. I'm scared. Recruiter "
            "{RECRUITER} won't help. My passport is {PASSPORT}. I came "
            "from {ORIGIN}. Phone {PHONE} -- DON'T call during the day. "
            "Email {EMAIL}. I live at {ADDRESS}."
        ),
    },
    {
        "id": "trafficking_indicators_combo",
        "category": "trafficking_combo",
        "template": (
            "{NAME}, {DOB}. Passport {PASSPORT} (held by employer). "
            "Recruiter: {RECRUITER}. Employer: {EMPLOYER}. Address: "
            "{ADDRESS}. Phone: {PHONE} (monitored). Email: {EMAIL}. "
            "Came from {ORIGIN} to {DEST}, paid {AMOUNT_USD} in fees. "
            "Multiple ILO indicators: passport retention, debt bondage, "
            "isolation, contract substitution. Need urgent help."
        ),
    },
]


# ===========================================================================
# 4. COMPOSITE GENERATOR (template fill + redaction plan)
# ===========================================================================
_PLACEHOLDER_RE = re.compile(r"\{([A-Z_]+)\}")
_PLACEHOLDER_TO_LABEL = {
    "NAME":       "PERSON",
    "FULL_NAME":  "PERSON",
    "FIRST_NAME": "PERSON",
    "LAST_NAME":  "PERSON",
    "PASSPORT":   "PASSPORT",
    "PHONE":      "PHONE",
    "EMAIL":      "EMAIL",
    "ADDRESS":    "ADDRESS",
    "RECRUITER":  "RECRUITER",
    "EMPLOYER":   "EMPLOYER",
    "DOB":        "DOB",
    "AMOUNT_USD": "AMOUNT_USD",
    "ORIGIN":     "ORIGIN_CITY",
    "DEST":       "DEST_CITY",
}
_GENERALIZABLE = {"ORIGIN_CITY", "DEST_CITY"}


def _hash_short(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _render_composite(rnd: random.Random, scenario: dict) -> dict:
    corridor_name = rnd.choice(list(_CORRIDORS.keys()))
    corridor = _CORRIDORS[corridor_name]
    template = scenario["template"]
    composite_parts: list[str] = []
    redacted_parts: list[str] = []
    redactions: list[dict] = []
    cursor_composite = 0
    last_end = 0
    for m in _PLACEHOLDER_RE.finditer(template):
        ph_kind = m.group(1)
        if ph_kind == "ORIGIN":
            value = corridor["origin"]
            label = "ORIGIN_CITY"
        elif ph_kind == "DEST":
            value = corridor["dest"]
            label = "DEST_CITY"
        else:
            label = _PLACEHOLDER_TO_LABEL.get(ph_kind, ph_kind)
            value = _synth_value(rnd, ph_kind, corridor)
        literal = template[last_end:m.start()]
        composite_parts.append(literal)
        redacted_parts.append(literal)
        cursor_composite += len(literal)
        span_start = cursor_composite
        composite_parts.append(value)
        cursor_composite += len(value)
        if label in _GENERALIZABLE:
            country = {
                "Manila": "the Philippines", "Cebu": "the Philippines",
                "Kathmandu": "Nepal", "Dhaka": "Bangladesh",
                "Surabaya": "Indonesia", "Hong Kong": "Hong Kong SAR",
                "Dubai": "the UAE", "Doha": "Qatar",
                "Riyadh": "Saudi Arabia",
            }.get(value, value)
            redacted_repr = (f"a city in {country}"
                              if label == "ORIGIN_CITY" else country)
            redacted_parts.append(redacted_repr)
        else:
            redacted_parts.append(f"[{label}]")
        redactions.append({
            "start": span_start,
            "end": cursor_composite,
            "label": label,
            "sha256_original": _hash_short(value),
        })
        last_end = m.end()
    composite_parts.append(template[last_end:])
    redacted_parts.append(template[last_end:])
    composite_text = "".join(composite_parts)
    redacted_text = "".join(redacted_parts)
    pii_categories = sorted({r["label"] for r in redactions})
    return {
        "composite_id": _hash_short(composite_text)[:12],
        "scenario": scenario["id"],
        "scenario_category": scenario["category"],
        "corridor": corridor_name,
        "composite_text": composite_text,
        "redacted_text": redacted_text,
        "redactions": redactions,
        "pii_categories": pii_categories,
        "n_redactions": len(redactions),
        "error": None,    # canonical PerRow.error (data_primitives.md 1.5)
    }


# ===========================================================================
# 5. RUN GENERATION
# ===========================================================================
print("\n" + "=" * 76)
print(f"[2/4] generating {N_COMPOSITES} synthetic PII composites")
print("=" * 76)

_rnd = random.Random(RANDOM_SEED)
_run_ts = time.strftime("%Y-%m-%dT%H-%M-%SZ", time.gmtime())
RUN_ID = f"a10_pii_synth_{_run_ts}"
COMPOSITE_PATH = OUTPUT_DIR / f"{RUN_ID}_pii_composite.json"
COMPOSITE_JSONL = OUTPUT_DIR / f"{RUN_ID}_pii_composite.jsonl"
GOLD_JSONL = OUTPUT_DIR / f"{RUN_ID}_pii_gold.jsonl"
METADATA_PATH = OUTPUT_DIR / f"{RUN_ID}_metadata.json"
BUNDLE_PATH = OUTPUT_DIR / f"{RUN_ID}_bundle.zip"
print(f"  run_id: {RUN_ID}")

_t0 = time.time()
dc_log("a10.synth.start", "PII synth generation beginning",
        run_id=RUN_ID, n_composites=N_COMPOSITES)

_composites: list[dict] = []
with COMPOSITE_JSONL.open("w", encoding="utf-8") as _comp_fh, \
     GOLD_JSONL.open("w", encoding="utf-8") as _gold_fh:
    for _i in range(N_COMPOSITES):
        _scenario = _rnd.choice(_SCENARIOS)
        _row = _render_composite(_rnd, _scenario)
        _composites.append(_row)
        _comp_fh.write(json.dumps(_row, ensure_ascii=False) + "\n")
        _gold_fh.write(json.dumps({
            "composite_id": _row["composite_id"],
            "messages": [
                {"role": "system", "content":
                 "You are a privacy-redaction assistant. Given an "
                 "intake note, return the same text with PII spans "
                 "replaced by [LABEL] tags. Generalize city names to "
                 "their country. Preserve everything else verbatim."},
                {"role": "user", "content": _row["composite_text"]},
                {"role": "assistant", "content": _row["redacted_text"]},
            ],
            "redactions": _row["redactions"],
        }, ensure_ascii=False) + "\n")
        if (_i + 1) % 50 == 0:
            print(f"  generated {_i + 1}/{N_COMPOSITES}")
            dc_log("a10.synth.progress", f"{_i + 1}/{N_COMPOSITES}",
                    completed=_i + 1, total=N_COMPOSITES)

_dur = time.time() - _t0
print(f"\n  generated {len(_composites)} composites in {_dur:.1f}s")

_summary = {
    "n_composites":   len(_composites),
    "n_scenarios":    len({c["scenario"] for c in _composites}),
    "n_corridors":    len({c["corridor"] for c in _composites}),
    "rows_per_scenario": {
        s["id"]: sum(1 for c in _composites if c["scenario"] == s["id"])
        for s in _SCENARIOS
    },
    "rows_per_corridor": {
        cn: sum(1 for c in _composites if c["corridor"] == cn)
        for cn in _CORRIDORS
    },
    "mean_redactions_per_composite": round(
        sum(c["n_redactions"] for c in _composites) /
        max(1, len(_composites)), 2),
    "duration_s": round(_dur, 2),
}

_payload = {
    "schema_version": "1.0",
    "kernel_id": "a-10-pii-synth-data-generator",
    "run_id": RUN_ID,
    "config": {
        "n_composites": N_COMPOSITES,
        "random_seed": RANDOM_SEED,
        "scenario_count": len(_SCENARIOS),
        "corridor_count": len(_CORRIDORS),
        "pii_categories": sorted(set(_PLACEHOLDER_TO_LABEL.values())),
        "generalizable_labels": sorted(_GENERALIZABLE),
    },
    "metadata": {
        "started_at": time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime(_t0)),
        "completed_at": time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "duration_s": round(_dur, 1),
        "kaggle_kernel_id": "a-10-pii-synth-data-generator",
        "host": "kaggle" if Path("/kaggle").exists() else "local",
    },
    "summary": _summary,
    "results": _composites,
}
COMPOSITE_PATH.write_text(
    json.dumps(_payload, indent=2, ensure_ascii=False), encoding="utf-8")
METADATA_PATH.write_text(
    json.dumps({k: v for k, v in _payload.items() if k != "results"},
                indent=2, ensure_ascii=False), encoding="utf-8")
print(f"  + {COMPOSITE_PATH.name}")
print(f"  + {COMPOSITE_JSONL.name}")
print(f"  + {GOLD_JSONL.name}")
print(f"  + {METADATA_PATH.name}")

with zipfile.ZipFile(BUNDLE_PATH, "w", zipfile.ZIP_DEFLATED) as _z:
    _z.writestr("manifest.json", json.dumps({
        "schema_version": "1.0",
        "run_id": RUN_ID,
        "kernel_id": "a-10-pii-synth-data-generator",
        "files": ["pii_composite.json", "pii_composite.jsonl",
                   "pii_gold.jsonl", "metadata.json"],
    }, indent=2))
    _z.write(COMPOSITE_PATH, "pii_composite.json")
    _z.write(COMPOSITE_JSONL, "pii_composite.jsonl")
    _z.write(GOLD_JSONL, "pii_gold.jsonl")
    _z.write(METADATA_PATH, "metadata.json")
print(f"  + {BUNDLE_PATH.name} "
      f"({BUNDLE_PATH.stat().st_size // 1024} KB)")

dc_log("a10.synth.done",
        f"PII synth complete ({len(_composites)} composites)",
        run_id=RUN_ID, n_composites=len(_composites),
        duration_s=int(_dur))


# ===========================================================================
# 6. WORKBENCH SHELL UI
# ===========================================================================
print("\n" + "=" * 76)
print("[3/4] launching summary UI (workbench shell)")
print("=" * 76)

_SHUTDOWN_EVENT = threading.Event()
_CLOUDFLARED_PROC: dict = {"p": None}

try:
    from duecare.chat.kernel_shell import build_minimal_shell
    summary_payload = {
        "title": (f"A-10 PII synthetic data run "
                   f"({len(_composites)} composites)"),
        "audience": "researcher",
        "lede": ("Generated synthetic intake notes with fake PII (names, "
                  "passports, phones, addresses, employers) paired with "
                  "gold redaction plans. Output JSONL is ready for the "
                  "A-11 PrivacyRedactor LoRA trainer. No real worker "
                  "data flowed through this kernel."),
        "results": [
            {"label": "Composites", "value": str(len(_composites))},
            {"label": "Scenarios",  "value": str(len(_SCENARIOS))},
            {"label": "Corridors",  "value": str(len(_CORRIDORS))},
            {"label": "Mean redactions/composite",
             "value": str(_summary["mean_redactions_per_composite"])},
            {"label": "Wall time", "value": f"{_dur:.1f}s"},
        ],
        "artifacts": [
            {"name": BUNDLE_PATH.name,    "path": str(BUNDLE_PATH)},
            {"name": COMPOSITE_PATH.name, "path": str(COMPOSITE_PATH)},
            {"name": COMPOSITE_JSONL.name, "path": str(COMPOSITE_JSONL)},
            {"name": GOLD_JSONL.name,     "path": str(GOLD_JSONL)},
            {"name": METADATA_PATH.name,  "path": str(METADATA_PATH)},
        ],
        "links": [
            ("Workbench (full)",
              "https://www.kaggle.com/code/taylorsamarel/duecare-exploration-workbench"),
            ("Experiment ladder spec",
              "https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/docs/appendix_experiment_ladder.md"),
        ],
        "next_steps": [
            f"Download {BUNDLE_PATH.name} from /artifact/{BUNDLE_PATH.name}.",
            "Publish the bundle as a Kaggle Dataset (or attach via Add "
            "Data) so A-11 can ingest the gold JSONL for LoRA training.",
            "For larger corpora, set DUECARE_N_PII_COMPOSITES=2000 "
            "and an alternative DUECARE_PII_SEED for a fresh run.",
        ],
    }
    app, public_url = build_minimal_shell(
        summary=summary_payload,
        kernel_id="a-10-pii-synth-data-generator",
        port=PORT,
    )
    if public_url:
        print(f"  ok UI available at {public_url}")
    print("\n" + "=" * 76)
    print("[4/4] A-10 PII SYNTH RUN COMPLETE")
    print("=" * 76)
    if public_url:
        print(f"\n   UI:     {public_url}")
    print(f"   bundle: /kaggle/working/{BUNDLE_PATH.name}\n")
    print("=" * 76)
    while not _SHUTDOWN_EVENT.is_set():
        time.sleep(1)
except KeyboardInterrupt:
    print("\n  interrupted -- shutting down")
except Exception as e:
    print(f"  shell unavailable: {type(e).__name__}: {e}")

print("\n  shutting down cleanly...")
try:
    if _CLOUDFLARED_PROC.get("p"):
        _CLOUDFLARED_PROC["p"].terminate()
except Exception:
    pass
print("  shutdown complete -- cell exiting.\n")
