"""Tests for scripts/hk_money_lenders.py -- HK Companies Registry money lenders.

Offline: the parser runs against the REAL row format observed in the live CR
PDF (MLR no / licence no / English [Chinese] name / expiry / R remark), with
synthetic licensee names. Download is exercised through an injected fetch.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


ml = _load("hk_money_lenders", _ROOT / "scripts" / "hk_money_lenders.py")

# real header/boilerplate + four data rows (synthetic names, real layout)
_PDF_TEXT = """\
現有放債人牌照持牌人名單 (截至 2026年4月30日) (依英文名稱字母次序)
List of Existing Money Lenders Licensees (as at 30 April 2026) (in alphabetical order of English Name)
檔案號碼 MLR No. 放債人牌照號碼 Money Lender's Licence No. 英文名稱 English Name 中文名稱 Chinese Name
6323 56/2026 001 Sample Credit Limited 001 樣本信貸有限公司 8-Nov-26
5762 1340/2025 10 Million Sample Credit Limited 千萬樣本信貸有限公司 8-Sep-26
6665 1880/2025 101 Sample Finance Group Limited 13-Jan-27
5399 0867/2025 28 Sample Loan Company Limited 易發樣本財務有限公司 16-Apr-26 R
Page 1 of 61
"""


def test_parse_extracts_only_data_rows():
    recs = ml.parse_ml_pdf(_PDF_TEXT)
    assert len(recs) == 4  # header + column-title + page-number lines skipped


def test_parse_fields_for_a_row():
    recs = ml.parse_ml_pdf(_PDF_TEXT)
    r = recs[0]
    assert r["license_no"] == "56/2026" and r["mlr_no"] == "6323"
    assert r["license_expiry"] == "8-Nov-26"
    assert r["name"] == "001 Sample Credit Limited"
    assert r["name_local"] == "樣本信貸有限公司"
    assert r["jurisdiction"] == "HK" and r["source_tier"] == "official"
    assert r["status_as_of"] == "30 April 2026"


def test_english_name_keeps_internal_numbers():
    # '10 Million...' -- the number is internal, not the Chinese column's prefix
    recs = ml.parse_ml_pdf(_PDF_TEXT)
    by = {r["license_no"]: r for r in recs}
    assert by["1340/2025"]["name"] == "10 Million Sample Credit Limited"


def test_row_without_chinese_name():
    recs = ml.parse_ml_pdf(_PDF_TEXT)
    r = next(r for r in recs if r["license_no"] == "1880/2025")
    assert r["name"] == "101 Sample Finance Group Limited" and r["name_local"] == ""


def test_renewal_remark_flag():
    recs = ml.parse_ml_pdf(_PDF_TEXT)
    r = next(r for r in recs if r["license_no"] == "0867/2025")
    assert r["renewal_in_progress"] is True
    assert r["name"] == "28 Sample Loan Company Limited"  # trailing R not in name


def test_split_en_cn_trims_chinese_latin_prefix():
    # '001 ...信貸' -> Latin '001' belongs to the Chinese column, trimmed off English
    en, cn = ml._split_en_cn("001 Sample Credit Limited 001 樣本信貸有限公司")
    assert en == "001 Sample Credit Limited" and cn.startswith("樣本")


def test_split_en_cn_no_chinese_returns_whole():
    en, cn = ml._split_en_cn("Sample Holdings 88 Limited")
    assert en == "Sample Holdings 88 Limited" and cn == ""


def test_parse_as_at():
    assert ml.parse_as_at("List ... (as at 30 April 2026) (...)") == "30 April 2026"
    assert ml.parse_as_at("no date here") == ""


def test_records_to_entities_maps_to_lender():
    recs = ml.parse_ml_pdf(_PDF_TEXT)
    ents = ml.records_to_entities(recs)
    assert all(e["entity_type"] == "lender" and e["jurisdiction"] == "HK" for e in ents)
    e = ents[0]
    assert "56/2026" in e["notes"] and e["source_tier"] == "official"
    assert "樣本信貸有限公司" in e["notes"]  # local name preserved in notes


def test_download_pdf_uses_injected_fetch():
    calls = []
    out = ml.download_pdf(fetch=lambda u: calls.append(u) or b"%PDF-FAKE")
    assert out == b"%PDF-FAKE" and calls == [ml.ML_PDF]


def test_empty_text_yields_no_records():
    assert ml.parse_ml_pdf("") == []
