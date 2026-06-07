"""Deterministic auto-graph builder for the acquisition pipeline (the "graphed"
step). Links each doc/chunk to domain ENTITIES (ILO conventions, corridors,
statutes, frameworks) and links docs to each other by shared entities -- so
retrieval can surface "see also" neighbours and the corpus is navigable.

Offline, stdlib, regex/gazetteer-based (NO model -- GLiNER/spaCy were AMBER
model-download per the tooling survey). Deterministic: same docs + vocabulary
-> same graph. Scalable: co-mention edges use an inverted entity->docs index, so
it does not pay the O(n^2) all-pairs cost on a 10k corpus.
"""
from __future__ import annotations

import re

from pydantic import BaseModel


class Edge(BaseModel):
    source: str
    target: str
    relation: str   # "mentions" (doc->entity) | "co_mentions" (doc<->doc)
    weight: int = 1


# Seed gazetteer: entity_id -> regex patterns (case-insensitive). Curated/verified,
# extensible; the acquisition pipeline may pass a larger vocabulary. Expanded
# 2026-06-06 (research-verified ILO conventions, instruments, statutes, bodies).
DEFAULT_VOCABULARY: dict[str, list[str]] = {
    # ILO conventions & protocols
    "ilo_c029": [r"\bc0?29\b", r"forced labour convention"],
    "ilo_c105": [r"\bc105\b", r"abolition of forced labour convention"],
    "ilo_c097": [r"\bc0?97\b", r"migration for employment convention"],
    "ilo_c143": [r"\bc143\b", r"migrant workers \(supplementary provisions\) convention"],
    "ilo_c181": [r"\bc181\b", r"private employment agencies convention"],
    "ilo_c188": [r"\bc188\b", r"work in fishing convention"],
    "ilo_c189": [r"\bc189\b", r"domestic workers convention"],
    "ilo_c190": [r"\bc190\b", r"violence and harassment convention"],
    "ilo_p029": [r"\bp0?29\b", r"protocol to the forced labour convention", r"forced labour protocol"],
    "mlc_2006": [r"\bmlc\s*,?\s*2006\b", r"maritime labour convention"],
    # international instruments / frameworks
    "palermo_protocol": [r"palermo protocol", r"trafficking in persons protocol",
                         r"trafficking in persons,? especially women and children"],
    "untoc": [r"\buntoc\b", r"convention against transnational organized crime"],
    "fatf": [r"\bfatf\b", r"financial action task force"],
    "bali_process": [r"bali process"],
    "colombo_process": [r"colombo process"],
    "abu_dhabi_dialogue": [r"abu dhabi dialogue"],
    "iris_iom": [r"international recruitment integrity system", r"\biris\b ethical recruitment"],
    "montreal_recommendations": [r"montreal recommendations"],
    "gcm_migration": [r"global compact for (?:safe,? orderly and regular )?migration"],
    "fair_recruitment": [r"general principles and operational guidelines for fair recruitment",
                         r"fair recruitment initiative"],
    # national statutes
    "ph_ra8042": [r"\br\.?a\.?\s?8042\b", r"migrant workers and overseas filipinos act"],
    "ph_ra10022": [r"\br\.?a\.?\s?10022\b"],
    "ph_ra9208": [r"\br\.?a\.?\s?9208\b", r"anti-trafficking in persons act of 2003"],
    "ph_ra10364": [r"\br\.?a\.?\s?10364\b", r"expanded anti-trafficking in persons act of 2012"],
    "ph_ra11862": [r"\br\.?a\.?\s?11862\b", r"expanded anti-trafficking in persons act of 2022"],
    "ph_ra11641": [r"\br\.?a\.?\s?11641\b", r"department of migrant workers act"],
    "us_tvpa": [r"\btvpa\b", r"trafficking victims protection act"],
    "uk_msa_2015": [r"modern slavery act 2015", r"transparency in supply chains"],
    "eu_dir_2011_36": [r"2011/36/eu", r"eu anti-trafficking directive"],
    "au_msa_2018": [r"modern slavery act 2018", r"australian modern slavery"],
    "nepal_fea_2007": [r"foreign employment act,?\s*(?:2064|2007)"],
    "bangladesh_oema_2013": [r"overseas employment and migrants act"],
    "indonesia_law18_2017": [r"protection of indonesian migrant workers", r"\bppmi\b"],
    "qatar_law19_2020": [r"law no\.?\s*19 of 2020", r"no[- ]objection certificate"],
    "kafala": [r"\bkafala\b", r"sponsorship system"],
    "non_punishment": [r"non-?punishment principle"],
    # bodies / agencies
    "ilo": [r"international labour organization", r"international labour office"],
    "iom": [r"international organization for migration"],
    "unodc": [r"united nations office on drugs and crime"],
    "greta": [r"\bgreta\b", r"group of experts on action against trafficking"],
    "ph_dmw_poea": [r"\bpoea\b", r"department of migrant workers",
                    r"philippine overseas employment administration"],
    "bangladesh_bmet": [r"\bbmet\b", r"bureau of manpower,? employment and training"],
    "nepal_dofe": [r"department of foreign employment"],
    "us_ilab": [r"\bilab\b", r"list of goods produced by child labor or forced labor"],
    "polaris": [r"polaris project"],
    "ijm": [r"international justice mission"],
    "ecpat": [r"\becpat\b"],
}
_CORRIDOR = re.compile(r"\b([A-Z]{2})-([A-Z]{2})\b")
# ISO 3166-1 alpha-2 codes (so XX-YY only counts as a migration corridor when both
# halves are real country codes -- avoids false positives like UN-HRC, HIV-AIDS, US-EU).
_ISO2 = frozenset(
    "AF AL DZ AD AO AG AR AM AU AT AZ BS BH BD BB BY BE BZ BJ BT BO BA BW BR BN BG BF "
    "BI KH CM CA CV CF TD CL CN CO KM CG CD CR CI HR CU CY CZ DK DJ DM DO EC EG SV GQ "
    "ER EE ET FJ FI FR GA GM GE DE GH GR GD GT GN GW GY HT HN HU IS IN ID IR IQ IE IL "
    "IT JM JP JO KZ KE KI KP KR KW KG LA LV LB LS LR LY LI LT LU MG MW MY MV ML MT MH "
    "MR MU MX FM MD MC MN ME MA MZ MM NA NR NP NL NZ NI NE NG NO OM PK PW PS PA PG PY "
    "PE PH PL PT QA RO RU RW KN LC VC WS SM ST SA SN RS SC SL SG SK SI SB SO ZA SS ES "
    "LK SD SR SE CH SY TW TJ TZ TH TL TG TO TT TN TR TM TV UG UA AE GB US UY UZ VU VE "
    "VN YE ZM ZW HK MO".split())


def extract_entities(text: str, vocabulary: dict[str, list[str]] | None = None) -> set[str]:
    """Deterministic gazetteer match -> set of entity ids found in ``text``.
    Corridors (e.g. PH-HK) are matched generically and emitted as
    ``corridor_XX-YY``."""
    vocab = vocabulary if vocabulary is not None else DEFAULT_VOCABULARY
    t = text or ""
    found: set[str] = set()
    for eid, pats in vocab.items():
        for p in pats:
            if re.search(p, t, re.I):
                found.add(eid)
                break
    for m in _CORRIDOR.finditer(t):  # only real country-code pairs are corridors
        a, b = m.group(1), m.group(2)
        if a != b and a in _ISO2 and b in _ISO2:
            found.add(f"corridor_{a}-{b}")
    return found


def build_graph(
    docs: list,
    *,
    text_of,
    id_of,
    vocabulary: dict[str, list[str]] | None = None,
    min_shared: int = 2,
) -> dict:
    """Build ``{nodes, edges}``: doc->entity ``mentions`` edges plus doc<->doc
    ``co_mentions`` edges (weight = #shared entities) when two docs share at
    least ``min_shared`` entities. Deterministic (all outputs sorted). Pure --
    returns data, writes nothing."""
    doc_ents: dict[str, set[str]] = {}
    edges: list[Edge] = []
    for d in docs:
        did = id_of(d)
        ents = extract_entities(text_of(d), vocabulary)
        doc_ents[did] = ents
        for e in sorted(ents):
            edges.append(Edge(source=did, target=e, relation="mentions"))

    # inverted index entity -> docs; pair only docs that share an entity
    inv: dict[str, list[str]] = {}
    for did in sorted(doc_ents):
        for e in doc_ents[did]:
            inv.setdefault(e, []).append(did)
    pair_shared: dict[tuple[str, str], int] = {}
    for dlist in inv.values():
        ds = sorted(set(dlist))
        for i in range(len(ds)):
            for j in range(i + 1, len(ds)):
                pair_shared[(ds[i], ds[j])] = pair_shared.get((ds[i], ds[j]), 0) + 1
    for (a, b), cnt in sorted(pair_shared.items()):
        if cnt >= min_shared:
            edges.append(Edge(source=a, target=b, relation="co_mentions", weight=cnt))

    nodes = sorted(set(doc_ents) | {e for ents in doc_ents.values() for e in ents})
    return {"nodes": nodes, "edges": [e.model_dump() for e in edges]}
