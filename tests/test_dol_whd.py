"""Tests for scripts/dol_whd.py -- DOL WHD enforcement -> employer-violation entity.

Offline + pure. The REC fixture is the dataset's own keyless preview row
(apiprod.dol.gov/v4/datasets/10362, captured 2026-06-19); MIGRANT is a synthetic row
exercising the H-2A/MSPA/child-labour violation surfacing. Pagination uses an injected fetch.
"""
from __future__ import annotations

import importlib.util
import sys
import urllib.parse
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


dol = _load("dol_whd", _ROOT / "scripts" / "dol_whd.py")

REC = {"case_id": 1428484, "trade_nm": "Reliant Energy",
       "legal_name": "Reliant Energy Retail Services, LLC", "street_addr_1_txt": "1000 Main",
       "cty_nm": "Houston", "st_cd": "TX", "zip_cd": "77002", "naic_cd": "09310",
       "naics_code_description": "State Generation and Distribution of Electric Power",
       "case_violtn_cnt": 0, "cmp_assd": 0.0, "ee_violtd_cnt": 1, "bw_atp_amt": 0.0,
       "ee_atp_cnt": 0, "findings_start_date": "2005-06-20T00:00:00",
       "findings_end_date": "2005-07-19T00:00:00", "flsa_violtn_cnt": 0}

MIGRANT = {"trade_nm": "Sunrise Farms LLC", "legal_name": "Sunrise Farms LLC",
           "street_addr_1_txt": "1 Vine Rd", "cty_nm": "Fresno", "st_cd": "CA", "naic_cd": "111",
           "naics_code_description": "Crop Production", "case_violtn_cnt": 12, "cmp_assd": 50000.0,
           "bw_atp_amt": 120000.0, "ee_atp_cnt": 45, "h2a_violtn_cnt": 8, "h2b_violtn_cnt": 0,
           "mspa_violtn_cnt": 3, "flsa_cl_violtn_cnt": 2,
           "findings_start_date": "2023-03-01T00:00:00", "findings_end_date": "2023-06-01T00:00:00"}


def test_parse_real_sample_row():
    e = dol.parse_record(REC)
    assert e["name"] == "Reliant Energy" and e["entity_type"] == "employer"
    assert e["address"] == "1000 Main, Houston, TX, 77002" and e["state"] == "TX"
    assert e["back_wages"] == 0.0 and e["violations"] == 0 and e["status"] == "no_violation"
    assert e["migrant_visa_violations"] == {} and e["findings_start"] == "2005-06-20"


def test_parse_surfaces_migrant_and_child_labour_violations():
    e = dol.parse_record(MIGRANT)
    assert e["migrant_visa_violations"] == {"h2a": 8, "mspa": 3}     # h2b=0 excluded
    assert e["child_labor_violations"] == 2
    assert e["back_wages"] == 120000.0 and e["employees_due"] == 45
    assert e["status"] == "violation"


def test_num_coerces():
    assert dol._num(None) == 0.0 and dol._num("12.5") == 12.5 and dol._num("x") == 0.0


def test_build_url_has_limit_and_offset():
    u = dol.build_url(limit=500, offset=50)
    assert "limit=500" in u and "offset=50" in u


def test_fetch_paginates_and_caps():
    def fetch(url):
        off = int(urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["offset"][0])
        return {"data": [dict(REC, case_id=off + i) for i in range(50)]} if off < 200 else {"data": []}
    ents = dol.fetch_enforcement(api_key="x", max_records=120, page_size=50, fetch=fetch)
    assert len(ents) == 120                                          # 50+50+20, capped


def test_load_dotenv_sets_missing_without_override(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text('DOL_API_KEY=abc123\n# comment\nKEEP_ME="quoted"\nALREADY=fromfile\n',
                   encoding="utf-8")
    monkeypatch.delenv("DOL_API_KEY", raising=False)
    monkeypatch.setenv("ALREADY", "preset")
    loaded = dol.load_dotenv(env)
    import os
    assert os.environ["DOL_API_KEY"] == "abc123" and os.environ["KEEP_ME"] == "quoted"
    assert os.environ["ALREADY"] == "preset"                        # existing env not overridden
    assert "DOL_API_KEY" in loaded and "ALREADY" not in loaded      # only newly-set names returned


def test_fetch_preview_parses_keyless_metadata_rows():
    import json
    meta = {"dataset": {"id": 10362, "dataset_preview": json.dumps({"data": [REC, MIGRANT]})}}
    ents = dol.fetch_preview(fetch=lambda url: json.dumps(meta))
    assert [e["name"] for e in ents] == ["Reliant Energy", "Sunrise Farms LLC"]
    assert ents[1]["migrant_visa_violations"] == {"h2a": 8, "mspa": 3}  # parsed via parse_record
