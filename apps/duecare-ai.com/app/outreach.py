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
  * Honest about sending: campaigns are DRAFT-ONLY. The hub never holds raw
    recipient addresses (subscribe persists sha256 + topics + org only), so
    there is nothing to send to from here by construction — a curator exports
    the draft to their own mailer. Collection (subscribe) and intake (inbound
    webhook) work regardless.
  * Privacy: subscriber emails are stored as sha256 only. Observation replies
    pass the same PII gate as the website form before becoming context
    signals, and rejected replies never surface facts publicly.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
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
    proposed: bool = False   # True for LLM-drafted gaps (vs the curated seed backbone)


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


# Canonical intent vocabulary — MUST stay aligned with automation.Intent
# (this module deliberately does not import automation; the alignment is
# asserted by tests/test_outreach.py against typing.get_args(Intent)).
# Informative intents confirm a gap; weights scale the context signal.
_CONFIRMING_INTENTS = frozenset({
    "verification", "new_information", "rule_proposal",
    "contact_update", "regulatory_change",
})
_INTENT_WEIGHTS: dict[str, float] = {
    "verification": 1.0,
    "new_information": 1.2,
    "rule_proposal": 1.1,
    "contact_update": 1.0,
    "regulatory_change": 1.1,
    "off_topic": 0.0,
    "unclear": 0.3,
}


def _signals_path(data_dir: Path) -> Path:
    return Path(data_dir) / "outreach_signals.jsonl"


def _campaigns_path(data_dir: Path) -> Path:
    return Path(data_dir) / "outreach_campaigns.jsonl"


def _proposed_gaps_path(data_dir: Path) -> Path:
    return Path(data_dir) / "outreach_proposed_gaps.jsonl"


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

def _gap_slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")[:48] or "gap"


def proposed_gap_spec_from_draft(item: dict[str, Any], *, model: str) -> dict[str, Any]:
    """An LLM outreach draft ``{topic, question, target_role}`` -> a PROPOSED gap spec.

    Proposed gaps extend the curated seed backbone: low base priority, ``kind="proposed"``,
    and a ``proposed`` flag the UI can badge. Sending stays draft-only / human-gated exactly
    as for seed gaps -- this only adds MORE questions a curator can choose to solicit on.
    """
    topic = str(item.get("topic") or "").strip()
    ask = str(item.get("question") or "").strip()
    audience = str(item.get("target_role") or "civil-society experts").strip()
    return {
        "id": "proposed_" + _gap_slug(topic or ask),
        "topic": topic or (ask[:60] or "Proposed context gap"),
        "corridor": str(item.get("corridor") or "multi"),
        "audience": audience,
        "ask": ask,
        "kind": "proposed",
        "base_priority": 0.4,   # below the curated seeds (0.5-0.7); never displaces them
        "proposed": True,
        "model": model,
    }


def _load_proposed_gaps(data_dir: Path) -> list[dict[str, Any]]:
    return _read_jsonl(_proposed_gaps_path(data_dir))


def ingest_proposed_gaps(data_dir: Path, drafts: list[dict[str, Any]], *, model: str,
                         ts: str) -> list[dict[str, Any]]:
    """Persist LLM outreach drafts as PROPOSED gaps (deduped by id). Returns the new specs.

    The drafts become solicitable gaps in ``detect_context_gaps``; a curator still reviews
    every drafted campaign and does the actual sending (the hub stores no raw addresses, so
    nothing is auto-sent by construction). The LLM only PROPOSES which questions to ask.
    """
    seen = {str(g.get("id")) for g in _load_proposed_gaps(data_dir)}
    added: list[dict[str, Any]] = []
    for it in drafts:
        if not isinstance(it, dict) or not str(it.get("question") or "").strip():
            continue
        spec = proposed_gap_spec_from_draft(it, model=model)
        if spec["id"] in seen:
            continue
        seen.add(spec["id"])
        _append_jsonl(_proposed_gaps_path(data_dir), {**spec, "ts": ts})
        added.append(spec)
    return added


def detect_context_gaps(data_dir: Path) -> list[ContextGap]:
    """Return the prioritized context gaps to solicit on.

    Priority = seed weight, boosted by how many civil-society observations
    have already confirmed/touched the gap (more field corroboration -> more
    worth deepening into curated context + candidate rubric dimensions).

    The curated ``_SEED_GAPS`` are the stable backbone; LLM-proposed gaps
    (human-reviewable, lower base priority) extend the list without displacing
    them, and never overwrite a seed id.
    """
    signals = _read_jsonl(_signals_path(data_dir))
    by_gap: dict[str, dict[str, int]] = {}
    for s in signals:
        gid = str(s.get("gap_id") or "")
        if not gid:
            continue
        agg = by_gap.setdefault(gid, {"n": 0, "confirm": 0})
        agg["n"] += 1
        if s.get("intent") in _CONFIRMING_INTENTS and s.get("verdict") != "reject":
            agg["confirm"] += 1

    gaps: list[ContextGap] = []
    seen_ids: set[str] = set()
    for spec in [*_SEED_GAPS, *_load_proposed_gaps(data_dir)]:
        gid = str(spec.get("id") or "")
        if not gid or gid in seen_ids:
            continue
        seen_ids.add(gid)
        agg = by_gap.get(gid, {"n": 0, "confirm": 0})
        g = ContextGap(
            id=gid, topic=spec["topic"], corridor=spec["corridor"],
            audience=spec["audience"], ask=spec["ask"], kind=spec["kind"],
            base_priority=float(spec["base_priority"]),
            signal_count=agg["n"], confirm_count=agg["confirm"],
            proposed=bool(spec.get("proposed", False)),
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
    send_status: str         # always "drafted" — the hub stores no raw
                             # addresses; a curator exports the draft to
                             # their own mailer
    model: str
    ts: str = ""


def _smtp_configured() -> bool:
    return bool(os.environ.get("DUECARE_SMTP_HOST") and os.environ.get("DUECARE_SMTP_FROM"))


def _norm(text: str) -> str:
    """Normalize for matching: lowercase, hyphens/underscores to spaces.

    Applied to BOTH sides so 'PH-HK' (the exact example the /outreach
    opt-in form suggests) matches a gap whose corridor normalizes to
    'ph hk'."""
    return (text or "").lower().replace("-", " ").replace("_", " ")


# Generic structure words excluded from gap-word matching so e.g. a
# subscriber interested in 'pattern' does not match every pattern gap.
_GAP_WORD_STOP = frozenset({"sector", "pattern", "currency", "reality"})


def _match_recipients(gap: ContextGap, subscribers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Pick opted-in subscribers whose topics/role plausibly match the gap.

    Matching is deliberately loose (corridor/kind token overlap, significant
    gap words like 'fishing', OR a blank/general-interest profile) so a thin
    contact list still reaches someone; the curator reviews every draft.
    """
    corridor_tok = _norm(gap.corridor)
    kind_tok = _norm(gap.kind)
    kind_head = gap.kind.split("_")[0]
    gap_words = {
        w for w in (_norm(gap.id) + " " + _norm(gap.topic)).split()
        if len(w) >= 4 and w not in _GAP_WORD_STOP
    }
    out: list[dict[str, Any]] = []
    for s in subscribers:
        if not s.get("consent_to_outreach", True):
            continue
        topics_raw = " ".join(str(t) for t in (s.get("topics") or []))
        role_raw = str(s.get("role") or "")
        hay = _norm(topics_raw + " " + role_raw)
        hay_words = set(hay.split())
        if ((not topics_raw and not role_raw)
                or corridor_tok in hay
                or kind_tok in hay
                or kind_head in hay
                or (gap_words & hay_words)
                or "all" in hay_words
                or "general" in hay_words):
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
        # Always "drafted": the hub stores subscriber emails as sha256 only,
        # so there is no address to send to from here by construction. A
        # curator exports the draft to their own mailer. (The old behaviour
        # claimed "queued" when DUECARE_SMTP was set, but no send
        # implementation existed — a real-not-faked violation.)
        send_status="drafted",
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
    structured fact came back; rejects carry ZERO weight (including the fact
    bonus — a gate-rejected reply must not pump public priorities) but are
    still logged server-side.
    """
    intent = getattr(verdict, "intent", "unclear")
    v = getattr(verdict, "verdict", "needs_curator_review")
    facts = list(getattr(verdict, "extracted_facts", []) or [])[:8]
    base = _INTENT_WEIGHTS.get(intent, 0.3)
    weight = 0.0 if v == "reject" else round(base + min(0.6, 0.15 * len(facts)), 3)
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
        # Skip gate-rejected signals entirely: with weight 0 they cannot
        # score, but without this filter their extracted "facts" would still
        # leak into the public sample_facts below.
        if gid not in gaps or s.get("verdict") == "reject":
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
