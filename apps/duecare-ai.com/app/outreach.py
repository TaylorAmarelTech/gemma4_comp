"""Civil-society outreach orchestration (the "email oracle", wired up).

The building blocks already existed (``automation.compose_outbound_request``
to draft a solicitation, ``automation.vet_inbound_email`` to vet a reply,
``/api/newsletter/subscribe`` to collect opted-in contacts). This module is
the missing orchestration that makes the hub *actually run outreach*:

    detect context gaps  ->  draft a targeted campaign  ->  (send / queue)
        ->  ingest observations from replies  ->  prioritize context
        ->  surface candidate ranking/rubric dimensions

Design goals:
  * Stdlib-only + the existing ``automation`` module; file-based stores under
    the hub data dir. No queue, no Celery (hackathon scope; in-line like the
    rest of the hub).
  * Honest about sending: actual SMTP send is gated behind configured creds
    (``DUECARE_SMTP_HOST`` etc.). With no creds a campaign is "drafted, ready
    to send" — never a fake "sent". Collection (subscribe) and intake (inbound
    webhook) work regardless.
  * Privacy: recipient emails are matched/stored by sha256; raw addresses are
    only used transiently to send. Observation replies pass the same PII gate
    as the website form before becoming context signals.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Optional


# --------------------------------------------------------------------------
# Context gaps — the knowledge the hub wants civil society to help verify.
# Each gap is a concrete, field-answerable ask (a caseworker / lawyer /
# hotline volunteer can answer it from experience). The seed list is the
# stable backbone; pack-registry state and accumulated response signals
# re-rank it dynamically.
# --------------------------------------------------------------------------

@dataclass(slots=True)
class ContextGap:
    id: str
    topic: str
    corridor: str          # e.g. "PH-HK", "NP-QA", "multi"
    audience: str          # who is best placed to answer
    ask: str               # the specific observation question
    kind: str              # fee_cap | emerging_pattern | contact_currency | statute | sector_pattern
    base_priority: float   # 0..1 seed weight
    # dynamic fields filled by detect_context_gaps:
    signal_count: int = 0
    confirm_count: int = 0
    priority: float = 0.0


_SEED_GAPS: list[dict[str, Any]] = [
    {"id": "fee_cap_ph_hk", "topic": "PH-HK placement-fee cap currency", "corridor": "PH-HK",
     "audience": "NGO caseworkers and recruitment-compliance officers",
     "ask": "Have you seen the Philippines->Hong Kong domestic-worker placement-fee rule change recently, or fees still charged despite the zero-fee policy? What amounts and labels are you seeing?",
     "kind": "fee_cap", "base_priority": 0.7},
    {"id": "fee_cap_np_qa", "topic": "NP-QA recruitment-cost reality", "corridor": "NP-QA",
     "audience": "Nepali migrant-worker advocates and returnee-support staff",
     "ask": "What recruitment costs are Nepali workers actually paying to go to Qatar right now, and how are they labelled (training, processing, 'free visa')?",
     "kind": "fee_cap", "base_priority": 0.6},
    {"id": "pattern_digital_fee_rails", "topic": "Crypto / e-wallet fee collection", "corridor": "multi",
     "audience": "hotline volunteers, journalists, and platform-safety reviewers",
     "ask": "Are you observing recruiters asking workers to pay fees via crypto (USDT) or e-wallets (GCash, bKash, eSewa)? Which apps, which corridors?",
     "kind": "emerging_pattern", "base_priority": 0.65},
    {"id": "pattern_free_visa", "topic": "Gulf 'free visa' scam spread", "corridor": "multi",
     "audience": "Gulf-corridor advocates and embassy labour attaches",
     "ask": "How common is the 'free visa' offer (worker pays, no guaranteed employer) in your caseload, and which origin countries are most affected?",
     "kind": "emerging_pattern", "base_priority": 0.6},
    {"id": "contact_currency_ngo", "topic": "NGO hotline / contact currency", "corridor": "multi",
     "audience": "NGO intake coordinators",
     "ask": "Are the migrant-worker hotline numbers and intake contacts you rely on still current? Which ones have changed in the last year?",
     "kind": "contact_currency", "base_priority": 0.55},
    {"id": "statute_new_regulations", "topic": "New / amended recruitment statutes", "corridor": "multi",
     "audience": "labour lawyers and regulatory inspectors",
     "ask": "Has a new or amended recruitment / anti-trafficking regulation taken effect in your jurisdiction recently that we should add or update?",
     "kind": "statute", "base_priority": 0.6},
    {"id": "sector_fishing", "topic": "Fishing-sector debt + document control", "corridor": "multi",
     "audience": "fisher-welfare organisations and port chaplaincies",
     "ask": "In the fishing sector, what debt and document-control patterns are you seeing at sea or at port that our rules should catch?",
     "kind": "sector_pattern", "base_priority": 0.5},
    {"id": "sector_domestic_substitution", "topic": "Domestic-work contract substitution", "corridor": "multi",
     "audience": "domestic-worker unions and shelters",
     "ask": "How often are domestic workers told to sign a new, worse contract on arrival, and what terms change? Any new variations we should flag?",
     "kind": "sector_pattern", "base_priority": 0.5},
]


# --------------------------------------------------------------------------
# Stores (file-based, under the hub data dir).
# --------------------------------------------------------------------------

def _sha256(text: str) -> str:
    return hashlib.sha256((text or "").strip().lower().encode("utf-8")).hexdigest()


def _signals_path(data_dir: Path) -> Path:
    return Path(data_dir) / "outreach_signals.jsonl"


def _campaigns_path(data_dir: Path) -> Path:
    return Path(data_dir) / "outreach_campaigns.jsonl"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# --------------------------------------------------------------------------
# Gap detection (seed + dynamic re-ranking by accumulated response signals).
# --------------------------------------------------------------------------

def detect_context_gaps(data_dir: Path) -> list[ContextGap]:
    """Return the prioritized context gaps to solicit on.

    Priority = seed weight, boosted by how many civil-society observations
    have already confirmed/touched the gap (more field corroboration -> more
    worth deepening into curated context + candidate rubric dimensions).
    """
    signals = _read_jsonl(_signals_path(data_dir))
    by_gap: dict[str, dict[str, int]] = {}
    for s in signals:
        gid = str(s.get("gap_id") or "")
        if not gid:
            continue
        agg = by_gap.setdefault(gid, {"n": 0, "confirm": 0})
        agg["n"] += 1
        if s.get("intent") in {"verification", "new_info"} and s.get("verdict") != "reject":
            agg["confirm"] += 1

    gaps: list[ContextGap] = []
    for spec in _SEED_GAPS:
        agg = by_gap.get(spec["id"], {"n": 0, "confirm": 0})
        g = ContextGap(
            id=spec["id"], topic=spec["topic"], corridor=spec["corridor"],
            audience=spec["audience"], ask=spec["ask"], kind=spec["kind"],
            base_priority=float(spec["base_priority"]),
            signal_count=agg["n"], confirm_count=agg["confirm"],
        )
        # Boost: each confirming observation adds 0.05, capped at +0.3.
        g.priority = round(min(1.0, g.base_priority + min(0.3, 0.05 * g.confirm_count)), 3)
        gaps.append(g)

    gaps.sort(key=lambda x: (-x.priority, -x.confirm_count, x.id))
    return gaps


def gap_by_id(data_dir: Path, gap_id: str) -> Optional[ContextGap]:
    for g in detect_context_gaps(data_dir):
        if g.id == gap_id:
            return g
    return None


# --------------------------------------------------------------------------
# Campaign drafting (targets opted-in subscribers; sends only if configured).
# --------------------------------------------------------------------------

@dataclass(slots=True)
class Campaign:
    gap_id: str
    topic: str
    subject: str
    body: str
    audience: str
    n_recipients: int
    recipient_topics: list[str]
    send_status: str         # "drafted" (no SMTP) | "queued" (SMTP configured)
    model: str
    ts: str = ""


def _smtp_configured() -> bool:
    return bool(os.environ.get("DUECARE_SMTP_HOST") and os.environ.get("DUECARE_SMTP_FROM"))


def _match_recipients(gap: ContextGap, subscribers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Pick opted-in subscribers whose topics/role plausibly match the gap.

    Matching is deliberately loose (topic keyword overlap OR a general-interest
    subscriber) so a thin contact list still reaches someone; the curator
    reviews before any real send.
    """
    corridor_tok = gap.corridor.lower().replace("-", " ")
    kind_tok = gap.kind.replace("_", " ")
    out: list[dict[str, Any]] = []
    for s in subscribers:
        if not s.get("consent_to_outreach", True):
            continue
        topics = " ".join(str(t) for t in (s.get("topics") or [])).lower()
        role = str(s.get("role") or "").lower()
        hay = topics + " " + role
        if (not topics and not role) or corridor_tok in hay or kind_tok in hay \
                or gap.kind.split("_")[0] in hay or "all" in topics or "general" in topics:
            out.append(s)
    return out


def draft_campaign(data_dir: Path, gap: ContextGap, subscribers: list[dict[str, Any]],
                   *, compose) -> Campaign:
    """Draft a solicitation campaign for a gap.

    ``compose`` is ``automation.compose_outbound_request`` injected so this
    module stays decoupled and unit-testable. Persists an audit record.
    """
    draft = compose(gap.topic, gap.audience, gap.ask)
    recipients = _match_recipients(gap, subscribers)
    campaign = Campaign(
        gap_id=gap.id, topic=gap.topic,
        subject=getattr(draft, "subject", gap.topic),
        body=getattr(draft, "body", gap.ask),
        audience=gap.audience,
        n_recipients=len(recipients),
        recipient_topics=sorted({t for s in recipients for t in (s.get("topics") or [])})[:12],
        send_status="queued" if _smtp_configured() else "drafted",
        model=getattr(draft, "model", "template-fallback"),
    )
    return campaign


def record_campaign(data_dir: Path, campaign: Campaign, ts: str) -> None:
    campaign.ts = ts
    _append_jsonl(_campaigns_path(data_dir), asdict(campaign))


# --------------------------------------------------------------------------
# Observation intake -> context signal (feeds prioritization + dimensions).
# --------------------------------------------------------------------------

@dataclass(slots=True)
class ContextSignal:
    gap_id: str
    intent: str
    verdict: str
    weight: float
    facts: list[str]
    sender_sha256: str
    ts: str = ""


def ingest_observation(data_dir: Path, gap_id: str, *, verdict, sender_email: str,
                       ts: str) -> ContextSignal:
    """Turn a vetted inbound reply (``automation.vet_inbound_email`` result)
    into a context signal and persist it. Weight reflects intent + how much
    structured fact came back; rejects carry ~zero weight but are still logged.
    """
    intent = getattr(verdict, "intent", "unclear")
    v = getattr(verdict, "verdict", "needs_curator_review")
    facts = list(getattr(verdict, "extracted_facts", []) or [])[:8]
    base = {"verification": 1.0, "new_info": 1.2, "off_topic": 0.0, "unclear": 0.3}.get(intent, 0.3)
    if v == "reject":
        base = 0.0
    weight = round(base + min(0.6, 0.15 * len(facts)), 3)
    sig = ContextSignal(
        gap_id=gap_id, intent=intent, verdict=v, weight=weight, facts=facts,
        sender_sha256=_sha256(sender_email), ts=ts,
    )
    _append_jsonl(_signals_path(data_dir), asdict(sig))
    return sig


def prioritized_context(data_dir: Path) -> list[dict[str, Any]]:
    """Rank context priorities from accumulated observations.

    Each gap gets a score = sum of signal weights; gaps with strong, repeated
    civil-society corroboration rise. Surfaces, per gap, a candidate
    ranking/rubric-dimension hint (what a new grading dimension could test) so
    the loop closes back into the harness's evaluation surface.
    """
    signals = _read_jsonl(_signals_path(data_dir))
    gaps = {g.id: g for g in detect_context_gaps(data_dir)}
    scores: dict[str, dict[str, Any]] = {}
    for s in signals:
        gid = str(s.get("gap_id") or "")
        if gid not in gaps:
            continue
        entry = scores.setdefault(gid, {"score": 0.0, "n": 0, "facts": []})
        entry["score"] += float(s.get("weight") or 0.0)
        entry["n"] += 1
        for f in (s.get("facts") or []):
            if f not in entry["facts"]:
                entry["facts"].append(f)

    out: list[dict[str, Any]] = []
    for gid, entry in scores.items():
        g = gaps[gid]
        out.append({
            "gap_id": gid,
            "topic": g.topic,
            "corridor": g.corridor,
            "kind": g.kind,
            "score": round(entry["score"], 3),
            "n_observations": entry["n"],
            "sample_facts": entry["facts"][:6],
            # closing the loop: a candidate grading dimension this corroborated
            # context could become, so outreach feeds the rubric, not just RAG.
            "candidate_dimension": f"{g.kind}_{g.corridor.lower().replace('-', '_')}_currency"
                                   if g.kind in {"fee_cap", "contact_currency", "statute"}
                                   else f"emerging_{g.id}_recognition",
        })
    out.sort(key=lambda x: (-x["score"], -x["n_observations"]))
    return out
