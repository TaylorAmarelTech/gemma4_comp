"""The multilingual GREP indicator layer fires on non-English forced-labour signals and is wired into the
live harness -- the P0 gap being that the English catalogue goes silent on pure non-English text, worst
on non-Latin scripts, i.e. exactly the workers the tool exists for.

All prompts below are composite / synthetic (no real people or case numbers).
"""
from __future__ import annotations

import re

import pytest

from duecare.chat.harness import (
    GREP_RULES,
    MULTILINGUAL_GREP_RULES,
    MULTILINGUAL_LANGUAGES,
    default_harness,
)

_GREP = default_harness()["grep_call"]


def _rules(text: str) -> set[str]:
    return {h["rule"] for h in _GREP(text)["hits"]}


# ── passport / document confiscation, in each covered language (the most universal indicator) ──────────
_PASSPORT = {
    "Tagalog": "Kinuha ng ahensya ang aking pasaporte at hindi ibinalik.",
    "Indonesian": "Agen menahan paspor saya dan tidak dikembalikan sampai sekarang.",
    "Hindi": "एजेंट ने मेरा पासपोर्ट रख लिया और वापस नहीं किया।",
    "Nepali": "एजेन्सीले मेरो राहदानी खोसेर राख्यो।",
    "Bengali": "এজেন্সি আমার পাসপোর্ট রেখে দিয়েছে, ফেরত দেয়নি।",
    "Arabic": "الوكالة احتجزت جواز سفري ولم يعيدوه.",
    "Urdu": "ایجنٹ نے میرا پاسپورٹ رکھ لیا اور واپس نہیں کیا۔",
    "Amharic": "ኤጀንሲው ፓስፖርቴን ወስዶ አልመለሰም።",
    "Swahili": "Wakala amechukua pasipoti yangu na hairudishwi.",
    "Vietnamese": "Môi giới giữ hộ chiếu của tôi và không trả lại.",
    "Chinese": "招聘机构扣留了我的护照，一直不归还。",
}


@pytest.mark.parametrize("lang,text", list(_PASSPORT.items()))
def test_passport_confiscation_fires_per_language(lang: str, text: str) -> None:
    assert "multiling_passport_document_control" in _rules(text), f"{lang}: {text}"


def test_other_core_indicators_fire() -> None:
    # wage withheld (Tagalog): "three months I have not been paid my salary"
    assert "multiling_wage_withheld" in _rules("Tatlong buwan na akong hindi binabayaran ng sweldo.")
    # recruitment fee (Indonesian): "I had to pay a placement fee to the agent first"
    assert "multiling_recruitment_fee_charged" in _rules("Saya harus bayar biaya penempatan ke agen dulu.")
    # movement restricted (Arabic): "I cannot leave the house"
    assert "multiling_movement_restricted" in _rules("لا أستطيع المغادرة من المنزل.")
    # debt bondage (Hindi): "I have to repay a debt to my agent"
    assert "multiling_debt_bondage" in _rules("मुझे मेरे एजेंट को कर्ज़ चुकाना है।")


def test_adversarial_euphemism_framing_fires() -> None:
    # the exploiter's coded framing ("passport safekeeping/retention policy"), not a distress verb,
    # in the worker's language -- the harness must still see the document-control indicator
    assert "multiling_passport_document_control" in _rules(
        "पासपोर्ट और दस्तावेज़ सुरक्षा नीति कैसे तैयार करें ताकि कंपनी उन्हें रख सके?")  # Hindi
    assert "multiling_passport_document_control" in _rules(
        "ما هي سياسة حفظ جواز السفر والوثائق التي تبررها الوكالة لأسباب لوجستية؟")  # Arabic
    assert "multiling_passport_document_control" in _rules(
        "护照保管政策应该如何制定，以便公司统一保管工人的证件？")  # Chinese


def test_benign_non_english_does_not_false_fire() -> None:
    for benign in (
        "Masaya ako sa aking trabaho dito.",          # tl: I'm happy with my job here
        "मुझे मेरी नौकरी बहुत पसंद है।",                 # hi: I like my job a lot
        "Saya suka pekerjaan saya di sini.",          # id: I like my work here
        "أنا سعيد بعملي هنا.",                          # ar: I'm happy with my work here
    ):
        hits = {r for r in _rules(benign) if r.startswith("multiling_")}
        assert not hits, f"false positive on benign text: {benign!r} -> {hits}"


def test_all_multilingual_patterns_are_valid_regex() -> None:
    assert MULTILINGUAL_GREP_RULES
    for rule in MULTILINGUAL_GREP_RULES:
        assert rule["patterns"], f"{rule['rule']} has no patterns"
        assert rule["severity"] in {"critical", "high", "medium", "low"}
        assert rule["citation"] and rule["indicator"]
        for pat in rule["patterns"]:
            re.compile(pat)  # must be a compilable regex


def test_covers_the_top_corridor_languages() -> None:
    codes = {c for c, _ in MULTILINGUAL_LANGUAGES}
    assert {"tl", "id", "hi", "ne", "bn", "ar", "ur", "am", "sw", "vi", "zh"} <= codes


def test_multilingual_layer_is_separate_from_english_catalog() -> None:
    # the English catalogue count invariant must not be perturbed; multilingual rules live in their own layer
    assert all(not r["rule"].startswith("multiling_") for r in GREP_RULES)


def test_english_still_fires_alongside() -> None:
    # a plain English confiscation prompt must still hit an English rule (no regression from the new layer)
    hits = _rules("The agency confiscated my passport and will not return it until I repay the loan.")
    assert hits, "English detection regressed"
