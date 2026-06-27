"""Tests for scripts/investigation_lens.py -- actors, connections (network + money), crime-script stage."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


il = _load("investigation_lens", _ROOT / "scripts" / "investigation_lens.py")


def test_actors_network_and_money_detected():
    text = ("The same recruiter placed multiple workers, and deductions were sent as remittances into a "
            "shell company whose beneficial owner profits.")
    a = il.investigation_analysis(text)
    assert "recruiter" in a["actors"]                     # actor role mapped
    assert a["considers_network"] is True                 # same recruiter / multiple workers / shell company
    assert a["considers_financial"] is True               # remittances / who profits
    assert "financial_flow" in a["connections"]


def test_isolated_case_has_no_network_or_money():
    a = il.investigation_analysis("A worker's passport was confiscated and wages withheld at the factory.")
    assert a["considers_network"] is False and a["considers_financial"] is False
    assert "control" in a["stages"]                        # passport / withheld wages -> control stage


def test_crime_stage_recruitment_detected():
    a = il.investigation_analysis("She was recruited in the village with a job offer before departure.")
    assert "recruitment" in a["stages"]


def test_coverage_aggregates_rates():
    networked = ("The same recruiter placed multiple workers; remittances flowed to a shell company.")
    isolated = "A general note about office supplies and weekly schedules."
    cov = il.coverage([networked, isolated])
    assert cov["n"] == 2
    assert cov["considers_network_rate"] == 0.5           # only the first reasons about the network
    assert "financial_flow" in cov["connection_rate"]
