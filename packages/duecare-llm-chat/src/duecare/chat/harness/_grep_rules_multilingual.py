"""Multilingual / transliterated GREP indicator rules for the trafficking harness.

WHY THIS EXISTS. The English ``GREP_RULES`` catalogue fires on English text (and, because English
trigger terms survive in real workers' romanised code-switched messages, on a lot of slang too), but it
degrades to nothing on *pure* non-English text -- worst on non-Latin scripts. That is the exact
population a migrant-worker safety tool exists for: a Filipino domestic worker writing in Tagalog, a
Nepali or Bangladeshi construction worker in Devanagari / Bengali, a Gulf-corridor worker in Arabic.
``scripts/grep_multilingual_coverage.py`` measures the gap; this module closes it.

WHAT IT DOES. For the highest-volume migration corridors' languages, it detects the core ILO
forced-labour indicators *in the worker's own language*, using compound proximity patterns (an
indicator noun -- passport, wage, fee, debt -- within a short window of a coercion context term --
"confiscated", "not paid", "cannot leave"). Requiring two exploitation-relevant terms near each other
keeps precision reasonable; and because the harness design is FLAG -> model, a multilingual GREP hit
routes the message to Gemma for the real reasoning, so this layer can only add reach, never subtract.

HOW IT INTEGRATES. ``duecare.chat.harness`` imports ``MULTILINGUAL_GREP_RULES`` and appends it to the
matcher's rule set (same ``{rule, patterns, severity, citation, indicator}`` schema as ``GREP_RULES``).
The English catalogue count is unchanged; this is a distinct, separately-counted layer. The matcher
lower-cases input before matching -- a no-op for caseless scripts -- so the Latin-script terms below are
stored lower-case and the non-Latin terms are matched verbatim.

HONEST SCOPE. This is a first-pass keyword layer over well-established, verifiable exploitation
vocabulary, not a definitive multilingual classifier. Coverage is deliberately conservative (terms the
author is confident about; more languages/terms are cheap to add to ``_LANGS`` and are tracked by the
coverage script). Extend by adding a language entry or terms and re-running the coverage metric.
"""
from __future__ import annotations

import re

# ── Per-language exploitation vocabulary ─────────────────────────────────────────────────────────────
# Each language contributes the nouns + coercion-context terms for the core indicators. Latin-script
# terms are lower-case (the matcher lower-cases input); non-Latin scripts are caseless. Keep terms
# high-signal and verifiable; a term that is too generic (e.g. bare "money") is intentionally omitted.
_LANGS: dict[str, dict[str, object]] = {
    "tl": {  # Tagalog / Filipino  (Philippines corridors)
        "name": "Tagalog",
        "passport": ["pasaporte", "pasport"],
        "agency": ["ahensya", "ahensiya", "ahente", "recruiter", "ahensyang"],
        "fee": ["placement fee", "recruitment fee", "prosesong bayad", "bayad sa ahensya", "singil"],
        "debt": ["utang"],
        "wage": ["sweldo", "suweldo", "sahod"],
        "retain": ["kinuha", "kinumpiska", "hawak", "hindi ibinalik", "hindi isinauli", "hindi ibabalik"],
        "unpaid": ["hindi binabayaran", "hindi binayaran", "walang sweldo", "hindi sinasahod", "hindi nagbayad"],
        "restrict": ["hindi makaalis", "hindi pwedeng umalis", "hindi pinapayagang umalis", "nakakulong",
                     "bawal lumabas", "hindi makalabas"],
    },
    "id": {  # Indonesian / Malay  (Indonesia -> Malaysia / Gulf)
        "name": "Indonesian",
        "passport": ["paspor"],
        "agency": ["agen", "agensi", "calo", "perekrut", "penyalur"],
        "fee": ["biaya penempatan", "biaya perekrutan", "biaya agen", "potongan", "bayaran"],
        "debt": ["utang", "hutang", "pinjaman"],
        "wage": ["gaji", "upah"],
        "retain": ["ditahan", "disita", "dipegang", "tidak dikembalikan", "menahan paspor", "diambil"],
        "unpaid": ["tidak dibayar", "belum dibayar", "gaji tidak dibayar", "tidak digaji"],
        "restrict": ["tidak boleh keluar", "dikurung", "tidak bisa pergi", "dilarang keluar",
                     "tidak diizinkan keluar"],
    },
    "vi": {  # Vietnamese  (Vietnam -> Taiwan fishing / manufacturing)
        "name": "Vietnamese",
        "passport": ["hộ chiếu"],
        "agency": ["môi giới", "đại lý", "cò"],
        "fee": ["phí môi giới", "phí tuyển dụng", "lệ phí", "tiền cọc"],
        "debt": ["nợ", "khoản vay"],
        "wage": ["lương", "tiền lương"],
        "retain": ["giữ hộ chiếu", "thu hộ chiếu", "tịch thu", "không trả lại", "giữ giấy tờ"],
        "unpaid": ["chưa trả lương", "không trả lương", "chưa được trả", "nợ lương"],
        "restrict": ["không thể rời", "không được ra ngoài", "bị nhốt", "không cho đi", "bị giam"],
    },
    "sw": {  # Swahili  (Kenya / Uganda -> Gulf)
        "name": "Swahili",
        "passport": ["pasipoti"],
        "agency": ["wakala", "dalali", "ajenti"],
        "fee": ["ada ya uajiri", "malipo ya wakala", "gharama za usafiri"],
        "debt": ["deni", "mkopo"],
        "wage": ["mshahara", "ujira"],
        "retain": ["kuchukua pasipoti", "kunyang'anya", "hairudishwi", "wamechukua", "walinyang'anya"],
        "unpaid": ["hawajanilipa", "sijalipwa", "hawakulipa", "mshahara haujalipwa"],
        "restrict": ["siwezi kuondoka", "sikuruhusiwi kutoka", "kufungiwa", "nimefungiwa ndani"],
    },
    "hi": {  # Hindi  (India -> Gulf)
        "name": "Hindi",
        "passport": ["पासपोर्ट", "पास्पोर्ट"],
        "agency": ["एजेंसी", "एजेंट", "दलाल", "भर्ती एजेंट"],
        "fee": ["फीस", "शुल्क", "भर्ती शुल्क", "एजेंट का पैसा"],
        "debt": ["कर्ज़", "कर्ज", "ऋण", "उधार"],
        "wage": ["वेतन", "तनख्वाह", "मजदूरी", "सैलरी"],
        "retain": ["रख लिया", "ले लिया", "जब्त", "वापस नहीं", "नहीं लौटा", "छीन लिया"],
        "unpaid": ["नहीं दिया", "वेतन नहीं", "पैसे नहीं दिए", "भुगतान नहीं", "तनख्वाह नहीं मिली"],
        "restrict": ["बाहर नहीं जा", "जाने नहीं दिया", "बंद कर दिया", "नहीं निकलने", "कैद"],
    },
    "ne": {  # Nepali  (Nepal -> Gulf / Malaysia)
        "name": "Nepali",
        "passport": ["राहदानी", "पासपोर्ट"],
        "agency": ["एजेन्सी", "एजेन्ट", "दलाल", "म्यानपावर"],
        "fee": ["शुल्क", "दस्तुर", "एजेन्सीको पैसा", "सेवा शुल्क"],
        "debt": ["ऋण", "कर्जा", "सापटी"],
        "wage": ["तलब", "ज्याला", "पारिश्रमिक"],
        "retain": ["राख्यो", "खोस्यो", "फिर्ता दिएन", "जफत", "खोसेर राख्यो"],
        "unpaid": ["तलब दिएन", "पैसा दिएन", "भुक्तानी दिएन", "तलब नदिएको"],
        "restrict": ["बाहिर जान दिएन", "निस्कन दिएन", "थुनेर राख्यो", "बन्द गरेर"],
    },
    "bn": {  # Bengali  (Bangladesh -> Malaysia / Gulf)
        "name": "Bengali",
        "passport": ["পাসপোর্ট"],
        "agency": ["এজেন্সি", "এজেন্ট", "দালাল"],
        "fee": ["ফি", "নিয়োগ ফি", "দালালের টাকা", "সার্ভিস চার্জ"],
        "debt": ["ঋণ", "দেনা", "ধার"],
        "wage": ["বেতন", "মজুরি"],
        "retain": ["রেখে দিয়েছে", "নিয়ে নিয়েছে", "জব্দ", "ফেরত দেয়নি", "কেড়ে নিয়েছে"],
        "unpaid": ["বেতন দেয়নি", "টাকা দেয়নি", "পরিশোধ করেনি", "বেতন পাইনি"],
        "restrict": ["বের হতে দেয় না", "বাইরে যেতে দেয় না", "আটকে রেখেছে", "বন্দি"],
    },
    "ur": {  # Urdu  (Pakistan -> Gulf)
        "name": "Urdu",
        "passport": ["پاسپورٹ"],
        "agency": ["ایجنسی", "ایجنٹ", "دلال"],
        "fee": ["فیس", "بھرتی فیس", "ایجنٹ کے پیسے"],
        "debt": ["قرض", "ادھار"],
        "wage": ["تنخواہ", "اجرت"],
        "retain": ["رکھ لیا", "ضبط", "واپس نہیں", "لے لیا", "چھین لیا"],
        "unpaid": ["نہیں دیا", "تنخواہ نہیں", "ادائیگی نہیں", "تنخواہ نہیں ملی"],
        "restrict": ["باہر نہیں جانے", "نکلنے نہیں", "قید", "بند کر"],
    },
    "ar": {  # Arabic  (Gulf + Lebanon destination, many origins)
        "name": "Arabic",
        "passport": ["جواز السفر", "جواز سفر", "الجواز"],
        "agency": ["وكالة", "مكتب الاستقدام", "الكفيل", "وسيط"],
        "fee": ["رسوم التوظيف", "رسوم الاستقدام", "عمولة", "أجرة الوكالة"],
        "debt": ["دين", "قرض", "سلفة"],
        "wage": ["راتب", "أجر", "الراتب"],
        "retain": ["احتجز", "صادر", "أمسك", "لم يعيد", "حجز الجواز", "سحب الجواز"],
        "unpaid": ["لم يدفع", "لم يصرف", "بدون راتب", "لا يدفع الراتب", "لم أستلم راتبي"],
        "restrict": ["لا أستطيع المغادرة", "ممنوع الخروج", "محتجز", "لا يسمح لي بالخروج", "محبوس"],
    },
    "am": {  # Amharic  (Ethiopia -> Gulf, incl. maritime).  Amharic inflects heavily with suffixes, so
        # noun/verb STEMS are used where the citation form would miss common possessive/gerund inflections
        # (e.g. ``ፓስፖር`` matches ``ፓስፖርት`` "passport" and ``ፓስፖርቴን`` "my passport").
        "name": "Amharic",
        "passport": ["ፓስፖር"],
        "agency": ["ኤጀንሲ", "ደላላ", "ወኪል"],
        "fee": ["የቅጥር ክፍያ", "የደላላ ገንዘብ", "ክፍያ"],
        "debt": ["ብድር", "ዕዳ"],
        "wage": ["ደመወዝ", "ክፍያ"],
        "retain": ["ወሰደ", "ወስዶ", "ያዘ", "አልመለሰም", "አልመልስም", "ወርሶ ያዘ"],
        "unpaid": ["አልከፈለም", "ደመወዝ አልከፈለም", "ክፍያ የለም"],
        "restrict": ["መውጣት አልችልም", "እንዳልወጣ", "ተዘግቶ", "ውጭ መውጣት አልተፈቀደም"],
    },
    "zh": {  # Chinese  (a major platform/recruitment language; PRC/Taiwan corridors)
        "name": "Chinese",
        "passport": ["护照", "護照"],
        "agency": ["中介", "招聘机构", "招聘機構", "中介公司", "经纪", "仲介"],
        "fee": ["中介费", "招聘费", "手续费", "工人费用", "工人支付的费用"],
        "debt": ["债务", "债", "贷款", "欠款"],
        "wage": ["工资", "薪水", "薪资"],
        "retain": ["扣留", "没收", "不归还", "扣押护照", "沒收"],
        "unpaid": ["拖欠工资", "没有支付工资", "未支付工资", "不发工资", "工资未付"],
        "restrict": ["不能离开", "不允许外出", "被关起来", "被困", "禁止外出", "不准离开"],
    },
    "si": {  # Sinhala  (Sri Lanka -> Gulf / Lebanon)
        "name": "Sinhala",
        "passport": ["ගමන් බලපත්‍රය", "විදේශ ගමන් බලපත්‍රය", "පාස්පෝට්"],
        "agency": ["ඒජන්සිය", "ඒජන්ට්", "නියෝජිත", "මැදිහත්කරු"],
        "fee": ["බඳවා ගැනීමේ ගාස්තුව", "ඒජන්සි ගාස්තුව", "ගාස්තුව"],
        "debt": ["ණය", "ණයක්"],
        "wage": ["වැටුප", "පඩිය"],
        "retain": ["රඳවා ගත්තා", "අත්පත් කර ගත්තා", "ආපසු දුන්නේ නැහැ", "දුන්නේ නැහැ"],
        "unpaid": ["වැටුප ගෙව්වේ නැහැ", "පඩිය දුන්නේ නැහැ", "ගෙවා නැහැ"],
        "restrict": ["පිට යන්න බැහැ", "පිටතට යාමට ඉඩ දෙන්නේ නැහැ", "හිර කරලා"],
    },
    "ta": {  # Tamil  (India / Sri Lanka -> Gulf).  Tamil is agglutinative, so the passport noun is stored
        # as a stem (``கடவுச்சீட்``) that prefixes both nominative ``கடவுச்சீட்டு`` and accusative ``கடவுச்சீட்டை``.
        "name": "Tamil",
        "passport": ["கடவுச்சீட்", "பாஸ்போர்ட்"],
        "agency": ["முகவர்", "ஏஜென்சி", "தரகர்"],
        "fee": ["ஆட்சேர்ப்பு கட்டணம்", "முகவர் கட்டணம்", "கட்டணம்"],
        "debt": ["கடன்"],
        "wage": ["சம்பளம்", "ஊதியம்"],
        "retain": ["வைத்துக்கொண்டார்", "பறிமுதல்", "திருப்பித் தரவில்லை", "எடுத்துக்கொண்டார்"],
        "unpaid": ["சம்பளம் தரவில்லை", "பணம் தரவில்லை", "கொடுக்கவில்லை"],
        "restrict": ["வெளியே போக முடியாது", "வெளியே அனுமதிக்கவில்லை", "அடைத்து"],
    },
    "my": {  # Burmese  (Myanmar -> Thailand / Malaysia -- Myanmar->Thailand is the highest-volume corridor)
        "name": "Burmese",
        "passport": ["နိုင်ငံကူးလက်မှတ်", "ပတ်စ်ပို့"],
        "agency": ["အေဂျင်စီ", "ပွဲစား", "အလုပ်ရှာဖွေရေး"],
        "fee": ["ဝန်ဆောင်ခ", "အခကြေးငွေ", "စေ့စပ်ခ"],
        "debt": ["အကြွေး", "ချေးငွေ"],
        "wage": ["လုပ်ခ", "လစာ"],
        "retain": ["သိမ်းထား", "ပြန်မပေး", "သိမ်းယူ", "ယူထား"],
        "unpaid": ["လစာမပေး", "ပိုက်ဆံမပေး", "မပေးဘူး"],
        "restrict": ["အပြင်မထွက်ရ", "ထွက်ခွင့်မပြု", "ချုပ်နှောင်"],
    },
}

# Document-retention EUPHEMISMS: the exploiter's coded framing ("passport safekeeping policy", "retention
# of documents for logistical/visa reasons") rather than a worker's distress verb ("took", "kept"). Added
# to each language's ``retain`` group so the passport rule catches BOTH the worker-side report and the
# adversarial euphemism. Compound phrases only (not bare "security" / "safekeeping"), to preserve precision
# -- they read as exploitation only when a passport/document term is within the window.
_RETAIN_EUPHEMISM: dict[str, list[str]] = {
    "tl": ["safekeeping", "para sa seguridad ang pasaporte", "kami ang maghahawak ng pasaporte"],
    "id": ["kebijakan penyimpanan paspor", "menyimpan paspor untuk keamanan", "penyimpanan dokumen"],
    "vi": ["chính sách giữ hộ chiếu", "giữ hộ chiếu để an toàn", "lưu giữ giấy tờ"],
    "sw": ["kutunza pasipoti", "sera ya kutunza hati", "kuhifadhi nyaraka"],
    "hi": ["सुरक्षा नीति", "दस्तावेज़ सुरक्षा", "पासपोर्ट सुरक्षित रखने", "हिफ़ाज़त"],
    "ne": ["राहदानी सुरक्षित राख्ने", "सुरक्षाका लागि राख्ने", "कागजात सुरक्षित"],
    "bn": ["সুরক্ষা নীতি", "নিরাপত্তা নীতি", "নথি সংরক্ষণ", "পাসপোর্ট সংরক্ষণ"],
    "ur": ["حفاظتی پالیسی", "پاسپورٹ محفوظ رکھنے", "دستاویزات کی حفاظت"],
    "ar": ["حفظ الوثائق", "حفظ جواز", "سياسة حفظ", "الاحتفاظ بالوثائق", "حفظ جواز السفر"],
    "am": ["ለደህንነት መጠበቅ", "ሰነድ መጠበቅ"],
    "zh": ["护照保管", "保管护照", "证件保管", "护照保管政策", "统一保管"],
    "si": ["ආරක්ෂිතව තබා ගැනීම", "ලේඛන ආරක්ෂණය"],
    "ta": ["பாதுகாப்பாக வைத்திருத்தல்", "ஆவணப் பாதுகாப்பு"],
    "my": ["လုံခြုံစွာ သိမ်းဆည်း", "စာရွက်စာတမ်း ထိန်းသိမ်း"],
}
for _code, _terms in _RETAIN_EUPHEMISM.items():
    if _code in _LANGS:
        _LANGS[_code]["retain"] = list(_LANGS[_code]["retain"]) + _terms  # type: ignore[operator]

# ── Rule generation ──────────────────────────────────────────────────────────────────────────────────
_WINDOW = 60   # chars between the two co-occurring terms: a clause-level window that catches both short
               # worker-distress messages ("agency took my passport") and the longer adversarial framing
               # ("...recruitment agency...the fee paid by the worker...") without spanning whole paragraphs


def _alt(terms: list[str]) -> str:
    """Regex alternation over escaped terms."""
    return "(?:" + "|".join(re.escape(t) for t in terms) + ")"


def _prox(a: list[str], b: list[str], window: int = _WINDOW) -> str:
    """Regex: any `a`-term within `window` chars of any `b`-term, either order (newline-safe)."""
    ga, gb = _alt(a), _alt(b)
    return f"{ga}[\\s\\S]{{0,{window}}}{gb}|{gb}[\\s\\S]{{0,{window}}}{ga}"


def _patterns(a_key: str, b_key: str) -> list[str]:
    """One proximity pattern per language that has BOTH term groups non-empty."""
    out: list[str] = []
    for spec in _LANGS.values():
        a, b = spec.get(a_key) or [], spec.get(b_key) or []
        if a and b:
            out.append(_prox(a, b))  # type: ignore[arg-type]
    return out


def _single(key: str) -> list[str]:
    """One alternation pattern per language for a single, self-sufficient term group."""
    return [_alt(spec[key]) for spec in _LANGS.values() if spec.get(key)]  # type: ignore[index]


MULTILINGUAL_LANGUAGES = [(code, spec["name"]) for code, spec in _LANGS.items()]

MULTILINGUAL_GREP_RULES = [
    {
        "rule": "multiling_passport_document_control",
        "patterns": _patterns("passport", "retain"),
        "severity": "critical",
        "citation": "ILO C029 (Forced Labour, 1930); ILO forced-labour indicator 'retention of identity "
                    "documents'; ICRMW (1990) Art. 21 (confiscation/destruction of ID or travel documents "
                    "unlawful except by an authorised official issuing a receipt).",
        "indicator": "Confiscation or non-return of a migrant worker's passport / travel document -- "
                     "detected in the worker's own language -- is one of the ILO's 11 forced-labour "
                     "indicators and is unlawful under ICRMW Art. 21 regardless of 'safekeeping' framing.",
    },
    {
        "rule": "multiling_recruitment_fee_charged",
        "patterns": _patterns("fee", "agency"),
        "severity": "high",
        "citation": "ILO C181 (Private Employment Agencies, 1997) Art. 7(1) (general prohibition on direct "
                    "or indirect fees to workers), subject to Art. 7(2) authorised exceptions for specified "
                    "worker categories; binding effect depends on ratification and domestic implementation. "
                    "ILO General Principles & Operational Guidelines for Fair Recruitment (2016), Principle 7.",
        "indicator": "Recruitment / placement fees charged to the worker by an agency or agent -- in the "
                     "worker's own language -- conflict with C181 Art. 7(1)'s general rule, while Art. 7(2), "
                     "ratification, and applicable domestic law must be checked before stating a binding "
                     "prohibition. Such fees are a major entry point to debt bondage.",
    },
    {
        "rule": "multiling_wage_withheld",
        "patterns": _patterns("wage", "unpaid"),
        "severity": "critical",
        "citation": "ILO C095 (Protection of Wages, 1949) Art. 12 (wages paid regularly); ILO forced-labour "
                    "indicator 7 (withholding of wages); UN Palermo Protocol Art. 3.",
        "indicator": "Withheld or unpaid wages reported in the worker's own language are ILO forced-labour "
                     "indicator 7 and violate ILO C095; when used to bind the worker to the employer they "
                     "are an element of trafficking under the Palermo Protocol.",
    },
    {
        "rule": "multiling_debt_bondage",
        "patterns": _patterns("debt", "agency"),
        "severity": "high",
        "citation": "ILO C029 + Forced Labour Protocol P029 (2014); ILO forced-labour indicator 4 (debt "
                    "bondage); UN Palermo Protocol Art. 3(a); 1956 Supplementary Slavery Convention Art. 1(a).",
        "indicator": "A debt owed by the worker to the recruiter / agency -- detected in the worker's own "
                     "language -- is the textbook ILO debt-bondage pattern (indicator 4) and a Palermo "
                     "Protocol 'means' of trafficking.",
    },
    {
        "rule": "multiling_movement_restricted",
        "patterns": _single("restrict"),
        "severity": "critical",
        "citation": "ILO C029 (Forced Labour, 1930); ILO forced-labour indicator 'restriction of movement'; "
                    "UN Palermo Protocol Art. 3 (means include coercion / confinement).",
        "indicator": "Restriction of a worker's freedom of movement -- 'cannot leave', 'not allowed out', "
                     "'locked in', in the worker's own language -- is a core ILO forced-labour indicator and "
                     "an element of trafficking under the Palermo Protocol.",
    },
]
