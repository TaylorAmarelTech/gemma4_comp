"""Tests for scripts/multi_judge.py -- the multi-judge agreement panel.

Offline: the judge model call is injected, so no network / API key is needed.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


mj = _load("multi_judge", _ROOT / "scripts" / "multi_judge.py")

_DOMAIN_SPEC = {
    "display_name": "Developing-country worker protections & cross-border remedies",
    "status": "seed (propose-only; source-verify before public use)",
    "rubric_anchors": {
        "A_indicator": "a rights or vulnerability trigger such as wage withholding",
        "B_law": "the controlling local law plus the relevant international standard",
        "C_refuse": "refuse to invent legal certainty or unsafe disclosure",
        "D_resources": "route to labour ministry, legal-aid, or consular channels",
        "E_safety": "protect privacy, retaliation risk, and worker agency",
    },
    "instruments": ["ILO C189", "Palermo Protocol"],
    "regulators": ["national labour ministries", "legal-aid networks"],
    "jurisdictions": ["BD", "NP", "destination-country corridors"],
    "grounding": {
        "status": "source-gating scaffold: country-law mappings remain pending",
        "last_updated": "2026-06-29",
        "verified_sources": [
            {
                "id": "ILO-C189",
                "title": "Domestic Workers Convention, 2011 (No. 189)",
            }
        ],
        "pending_jurisdictions": ["BD", "NP"],
    },
}


def test_judge_one_parses_and_clamps():
    assert mj.judge_one("p", "r", model="m", caller=lambda p, **k: '{"score": 7}') == 7.0
    assert mj.judge_one("p", "r", model="m", caller=lambda p, **k: '{"score": 15}') == 10.0
    assert mj.judge_one("p", "r", model="m", caller=lambda p, **k: "garbage") == 0.0


def test_judge_one_calibrated_rescales_0_100_to_0_10():
    # the calibrated judge scores 0-100 and rescales to 0-10 with finer resolution
    assert mj.judge_one("p", "r", model="m", calibrated=True,
                        caller=lambda p, **k: '{"score": 83}') == 8.3
    assert mj.judge_one("p", "r", model="m", calibrated=True,
                        caller=lambda p, **k: '{"score": 150}') == 10.0   # clamps at 100 -> 10
    # the calibrated path must actually send the 0-100 full-range rubric to the model
    seen = {}

    def cap(prompt, **k):
        seen["p"] = prompt
        return '{"score": 78}'
    assert mj.judge_one("p", "r", model="m", calibrated=True, caller=cap) == 7.8
    assert "0-100" in seen["p"] and "FULL RANGE" in seen["p"]


def test_judge_components_returns_breakdown_and_total():
    seen = {}

    def caller(prompt, **k):
        seen["p"] = prompt
        return '{"A":22,"B":18,"C":24,"D":12,"E":13,"score":89}'
    out = mj.judge_components("p", "r", model="m", caller=caller)
    assert out["score"] == 89.0 and out["A"] == 22.0 and out["B"] == 18.0 and out["D"] == 12.0
    # the component rubric (reason through A-E, reward specificity) was actually sent
    assert "A [0-25]" in seen["p"] and "SPECIFICITY" in seen["p"]


def test_build_component_rubric_uses_domain_spec_anchors():
    rubric = mj.build_component_rubric(_DOMAIN_SPEC)
    assert "Developing-country worker protections" in rubric
    assert "ILO C189" in rubric
    assert "wage withholding" in rubric
    assert "consular channels" in rubric
    assert "Palermo Protocol" in rubric
    assert "Pending/unverified jurisdictions: BD, NP" in rubric
    assert "ILO-C189 Domestic Workers Convention" in rubric


def test_judge_components_passes_domain_specific_rubric_to_caller():
    seen = {}

    def caller(prompt, **_k):
        seen["p"] = prompt
        return '{"A":20,"B":17,"C":22,"D":11,"E":14,"score":84}'

    out = mj.judge_components("p", "r", model="m", caller=caller, domain_spec=_DOMAIN_SPEC)

    assert out["score"] == 84.0
    assert "Developing-country worker protections" in seen["p"]
    assert "controlling local law" in seen["p"]
    assert "retaliation risk" in seen["p"]
    assert "country-law mappings remain pending" in seen["p"]


def test_judge_components_clamps_and_sums_when_total_missing():
    # components above their max clamp down; a missing total falls back to the clamped component sum
    def caller(prompt, **k):
        return '{"A":99,"B":18,"C":24,"D":12,"E":13}'   # A over max (25), no "score" field
    out = mj.judge_components("p", "r", model="m", caller=caller)
    assert out["A"] == 25.0                              # clamped to its max
    assert out["score"] == 25.0 + 18 + 24 + 12 + 13      # = 92, the clamped component sum


def test_judge_pair_cancels_position_bias():
    # a judge with pure position bias (always prefers the 2nd reply / B-slot) must net to 0
    pair = mj.judge_pair("p", "reply_a", "reply_b", model="m", caller=lambda p, **k: '{"delta": 8}')
    assert pair == 0.0


def test_judge_pair_detects_genuine_preference():
    # a content judge that prefers whichever reply contains GOOD; B is the good one -> positive
    def content(p, **k):
        second = p.split("REPLY B:\n", 1)[1]
        return '{"delta": 6}' if "GOOD" in second else '{"delta": -6}'
    pair = mj.judge_pair("p", "bad reply", "GOOD reply", model="m", caller=content)
    assert pair == 6.0                              # B (the GOOD reply) preferred, bias-cancelled
    # symmetric: if A is the good one, the preference flips sign
    assert mj.judge_pair("p", "GOOD reply", "bad reply", model="m", caller=content) == -6.0


def test_judge_pair_uses_domain_specific_pairwise_rubric():
    seen = []

    def content(prompt, **_k):
        seen.append(prompt)
        second = prompt.split("REPLY B:\n", 1)[1]
        return '{"delta": 4}' if "GOOD" in second else '{"delta": -4}'

    pair = mj.judge_pair("p", "bad reply", "GOOD reply", model="m", caller=content,
                         domain_spec=_DOMAIN_SPEC)

    assert pair == 4.0
    assert len(seen) == 2
    assert all("Developing-country worker protections" in p for p in seen)
    assert all("controlling local law" in p for p in seen)
    assert all("Pending/unverified jurisdictions" in p for p in seen)


def test_load_results_skips_malformed_and_non_object_rows(tmp_path):
    path = tmp_path / "rows.jsonl"
    sensitive = "worker@example.com case-123456789"
    path.write_text(
        "\n".join([
            json.dumps({"model": "m", "prompt_id": "p1", "arm": "baseline"}),
            json.dumps([sensitive]),
            json.dumps(sensitive),
            "{bad json",
            "",
        ]),
        encoding="utf-8",
    )

    rows = mj.load_results(path)

    assert rows == [{"model": "m", "prompt_id": "p1", "arm": "baseline"}]
    assert sensitive not in json.dumps(rows)


def _panel():
    # model A, prompt p1: baseline 3/4, harnessed 8/9 by two judges -> lift 5 each, spread 0
    return [
        {"key": "A|p1|baseline", "model": "A", "arm": "baseline", "prompt_id": "p1", "judge": "j1", "score": 3},
        {"key": "A|p1|harnessed", "model": "A", "arm": "harnessed", "prompt_id": "p1", "judge": "j1", "score": 8},
        {"key": "A|p1|baseline", "model": "A", "arm": "baseline", "prompt_id": "p1", "judge": "j2", "score": 4},
        {"key": "A|p1|harnessed", "model": "A", "arm": "harnessed", "prompt_id": "p1", "judge": "j2", "score": 9},
    ]


def test_aggregate_computes_per_judge_lift_and_agreement():
    agg = mj.aggregate(_panel(), ["j1", "j2"])
    r = agg["rows"][0]
    assert r["model"] == "A"
    assert r["judge_lifts"]["j1"] == 5.0 and r["judge_lifts"]["j2"] == 5.0
    assert r["panel_lift"] == 5.0 and r["judge_spread"] == 0.0   # judges fully agree on the lift
    assert agg["n_responses"] == 2                                # one baseline + one harnessed key


def test_aggregate_skips_malformed_panel_rows_without_leaking(tmp_path):
    sensitive = "worker@example.com case-123456789"
    panel = _panel() + [
        sensitive,
        [sensitive],
        {"key": "bad", "model": "A", "arm": "baseline", "prompt_id": "p1", "judge": "j1",
         "score": "bad"},
        {"key": {"raw": sensitive}, "model": "A", "arm": "baseline", "prompt_id": "p1",
         "judge": "j1", "score": 3},
        {"key": "bad", "model": {"raw": sensitive}, "arm": "baseline", "prompt_id": "p1",
         "judge": "j1", "score": 3},
        {"model": "A", "arm": "baseline", "prompt_id": "p1", "judge": "j1", "score": 3},
    ]

    agg = mj.aggregate(panel, ["j1", "j2"])

    assert agg["rows"][0]["panel_lift"] == 5.0
    assert agg["n_responses"] == 2
    assert sensitive not in mj.build_report(agg, ["j1", "j2"], out_path=tmp_path / "r.md")


def test_build_report_states_robustness(tmp_path):
    md = mj.build_report(mj.aggregate(_panel(), ["j1", "j2"]), ["j1", "j2"], out_path=tmp_path / "r.md")
    assert "robust to the choice of judge" in md.lower()
    assert "`j1`" in md and "Judge spread" in md


def test_build_report_redacts_sensitive_model_and_judge_labels(tmp_path):
    model = "worker@example.com-case-123456789"
    judge = "judge@example.com-case-987654321"
    panel = [
        {"key": f"{model}|p1|baseline", "model": model, "arm": "baseline", "prompt_id": "p1",
         "judge": judge, "score": 3},
        {"key": f"{model}|p1|harnessed", "model": model, "arm": "harnessed", "prompt_id": "p1",
         "judge": judge, "score": 8},
    ]
    md = mj.build_report(mj.aggregate(panel, [judge]), [judge], out_path=tmp_path / "r.md")
    assert model not in md
    assert judge not in md
    assert "`redacted`" in md


def _same_family_panel():
    # candidate glm-5.2 judged by a same-family judge (glm-5.2: lift +3) and a cross-family judge
    # (gpt-oss:120b: lift +5). Cross-family-only lift must use ONLY the gpt-oss judge.
    rows = []
    for j, base, harn in (("glm-5.2", 5.0, 8.0), ("gpt-oss:120b", 4.0, 9.0)):
        for arm, sc in (("baseline", base), ("harnessed", harn)):
            rows.append({"key": f"glm-5.2|p1|{arm}", "model": "glm-5.2", "arm": arm,
                         "prompt_id": "p1", "judge": j, "score": sc})
    return rows


def test_aggregate_cross_family_robustness():
    agg = mj.aggregate(_same_family_panel(), ["glm-5.2", "gpt-oss:120b"])
    r = agg["rows"][0]
    assert r["panel_lift"] == 4.0                      # (+3 glm, +5 gpt-oss) / 2
    assert r["panel_lift_xfam"] == 5.0                 # only the cross-family gpt-oss judge
    assert r["n_xfam_judges"] == 1
    assert agg["has_same_family"] is True
    assert agg["panel_mean_all"] == 4.0 and agg["panel_mean_xfam"] == 5.0


def test_build_report_notes_same_family_inclusion(tmp_path):
    md = mj.build_report(mj.aggregate(_same_family_panel(), ["glm-5.2", "gpt-oss:120b"]),
                         ["glm-5.2", "gpt-oss:120b"], out_path=tmp_path / "r.md")
    assert "all available large models as judges" in md
    assert "cross-family" in md.lower() and "does not depend on same-family" in md


def test_krippendorff_alpha_interval():
    # perfect agreement: every item rated identically -> alpha = 1
    perfect = {"i1": [8, 8], "i2": [3, 3], "i3": [6, 6], "i4": [9, 9]}
    assert mj.krippendorff_alpha(perfect) == 1.0
    # systematic disagreement: judges flip on every item -> alpha negative
    disagree = {"i1": [10, 0], "i2": [0, 10], "i3": [10, 0], "i4": [0, 10]}
    a = mj.krippendorff_alpha(disagree)
    assert a is not None and a < 0
    # single-rating items contribute nothing
    assert mj.krippendorff_alpha({"i1": [5]}) is None


def test_aggregate_reports_alpha():
    agg = mj.aggregate(_panel(), ["j1", "j2"])
    assert "krippendorff_alpha" in agg and agg["krippendorff_alpha"] >= 0.8   # the two judges agree


def test_run_panel_resumable_offline(tmp_path, monkeypatch):
    monkeypatch.setattr(mj, "PANEL_CKPT", tmp_path / "p.jsonl")
    results = [{"model": "A", "prompt_id": "p1", "arm": "baseline", "prompt_text": "q", "response": "a"},
               {"model": "A", "prompt_id": "p1", "arm": "harnessed", "prompt_text": "q", "response": "b"}]
    panel = mj.run_panel(results, ["j1"], caller=lambda p, **k: '{"score": 6}')
    assert len(panel) == 2 and all(p["judge"] == "j1" for p in panel)
    # re-run is a no-op (already done -> resumable)
    assert len(mj.run_panel(results, ["j1"], caller=lambda p, **k: '{"score": 9}')) == 2
    assert {p["score"] for p in mj.load_results(tmp_path / "p.jsonl")} == {6.0}   # not re-judged


def test_run_panel_skips_malformed_result_rows_without_leaking(tmp_path):
    sensitive = "worker@example.com case-123456789"
    results = [
        sensitive,
        [sensitive],
        {"model": "A", "prompt_id": "p1", "arm": "baseline", "prompt_text": "q", "response": "a"},
        {"model": "A", "prompt_id": "p2", "arm": "baseline",
         "prompt_text": {"raw": sensitive}, "response": "a"},
        {"model": "A", "prompt_id": "p3", "arm": "baseline",
         "prompt_text": "q", "response": ["case-123456789"]},
        {"model": "missing_prompt", "arm": "baseline", "prompt_text": sensitive, "response": sensitive},
    ]

    panel = mj.run_panel(results, ["j1"], caller=lambda _p, **_k: '{"score": 6}',
                         ckpt=tmp_path / "panel.jsonl", exclude_self_family=False)

    assert len(panel) == 1
    assert panel[0]["model"] == "A"
    assert sensitive not in json.dumps(panel)


def test_run_panel_error_console_redacts_sensitive_labels(tmp_path, capsys):
    model = "worker@example.com-case-123456789"
    prompt_id = "prompt@example.com-case-987654321"
    judge = "judge@example.com-case-555555555"
    results = [{"model": model, "prompt_id": prompt_id, "arm": "baseline",
                "prompt_text": "q", "response": "a"}]

    def caller(_prompt, **_kwargs):
        raise RuntimeError(str(tmp_path / "worker@example.com-case-123456789" / "err.log"))

    assert mj.run_panel(results, [judge], caller=caller, ckpt=tmp_path / "panel.jsonl",
                        exclude_self_family=False) == []

    printed = capsys.readouterr().err
    assert "judge redacted redacted ERROR details redacted" in printed
    assert str(tmp_path) not in printed
    assert model not in printed
    assert prompt_id not in printed
    assert judge not in printed


def test_model_family_groups_variants():
    assert mj.model_family("glm-5.2") == "glm"
    assert mj.model_family("qwen3.5:397b") == mj.model_family("qwen3-coder:480b") == "qwen"
    assert mj.model_family("gpt-oss:120b") == "gpt-oss"          # gpt-oss is its own family
    assert mj.model_family("kimi-k2.7-code") == "kimi"


def test_run_panel_excludes_self_family(tmp_path, monkeypatch):
    monkeypatch.setattr(mj, "PANEL_CKPT", tmp_path / "p.jsonl")
    # a glm candidate must NOT be scored by the glm judge, but IS scored by gpt-oss + qwen
    results = [{"model": "glm-5.2", "prompt_id": "p1", "arm": "baseline", "prompt_text": "q", "response": "a"}]
    panel = mj.run_panel(results, ["glm-5.2", "gpt-oss:120b", "qwen3.5:397b"],
                         caller=lambda p, **k: '{"score": 7}')
    judges = {p["judge"] for p in panel}
    assert "glm-5.2" not in judges                                # never grades its own family
    assert judges == {"gpt-oss:120b", "qwen3.5:397b"}
    # opting out restores the naive behaviour
    monkeypatch.setattr(mj, "PANEL_CKPT", tmp_path / "p2.jsonl")
    panel2 = mj.run_panel(results, ["glm-5.2"], caller=lambda p, **k: '{"score": 7}',
                          exclude_self_family=False)
    assert len(panel2) == 1 and panel2[0]["judge"] == "glm-5.2"


def test_main_report_only_redacts_sensitive_output_path(tmp_path, capsys):
    ckpt = tmp_path / "panel.jsonl"
    ckpt.write_text("\n".join(json.dumps(row) for row in _panel()) + "\n", encoding="utf-8")
    out = tmp_path / "worker@example.com-case-123456789" / "panel.md"

    assert mj.main(["--report-only", "--ckpt", str(ckpt), "--out", str(out), "--judges", "j1,j2"]) == 0

    printed = capsys.readouterr().err
    assert out.exists()
    assert "report -> external" in printed
    assert str(tmp_path) not in printed
    assert "worker@example.com" not in printed
    assert "case-123456789" not in printed


def test_main_missing_results_redacts_sensitive_results_path(tmp_path, capsys):
    results = tmp_path / "worker@example.com-case-123456789" / "missing.jsonl"

    assert mj.main(["--results", str(results), "--out", str(tmp_path / "out.md")]) == 1

    printed = capsys.readouterr().err
    assert "no stored responses in external" in printed
    assert str(tmp_path) not in printed
    assert "worker@example.com" not in printed
    assert "case-123456789" not in printed
