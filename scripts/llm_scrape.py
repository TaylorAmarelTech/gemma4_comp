#!/usr/bin/env python3
"""LLM-powered scraper: render -> screenshot + HTML -> model extracts structure.

A modern scraper does not hand-write a CSS selector per site. It renders the
page in a real browser, lets the model UNDERSTAND it, and extracts the fields
you ask for. This combines (informed by the Kaggle scraping notebooks -- the
crawl4ai LLM-extraction pattern, the headless-browser-on-Kaggle recipes, and
BeautifulSoup HTML cleaning):

  1. BROWSER render (Playwright -- reuses scripts/browser_scrape.py's launcher,
     which falls back to system Edge when the bundled chromium will not start).
  2. SCREENSHOT capture -> Gemma 4 VISION can read pages whose DOM is opaque
     (canvas, images, weird markup). Makes the model's multimodal feature
     load-bearing.
  3. HTML CLEAN (stdlib parser strips script/style/chrome -> visible text +
     links) so the model gets signal, not markup noise.
  4. LLM EXTRACT: the model turns the cleaned text (and/or the screenshot) into
     the structured fields you requested -- generalising past per-site schemas.

Design (matches the pipeline): the renderer and the model callables are all
INJECTABLE, so HTML cleaning, extraction prompting, JSON parsing, and the
orchestration are tested offline with no browser / GPU / network. Live text
extraction uses any OpenAI-compatible/Ollama endpoint; vision uses a multimodal
one (Gemma 4). Propose-only output.

Usage:
    python scripts/llm_scrape.py --url https://example.gov/agency/123 \
        --fields name,license_no,status,address,phone,email --screenshot
"""
from __future__ import annotations

import argparse
import base64
import importlib.util
import json
import os
import re
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _sibling(name: str):
    spec = importlib.util.spec_from_file_location(
        f"dc_{name}_for_llmscrape", str(_ROOT / "scripts" / f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


# ---- HTML cleaning (deterministic, stdlib) --------------------------------

class _Cleaner(HTMLParser):
    """Collect visible text + link/label hints; drop script/style/nav noise."""

    _SKIP = {"script", "style", "noscript", "svg", "head", "meta", "link"}

    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP:
            self._skip_depth += 1
        elif tag in ("br", "p", "div", "tr", "li", "h1", "h2", "h3", "td", "th"):
            self.parts.append("\n")
        elif tag == "a":
            href = dict(attrs).get("href", "")
            if href and not href.startswith(("javascript:", "#")):
                self.parts.append(f" [{href}] ")

    def handle_endtag(self, tag):
        if tag in self._SKIP and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data):
        if not self._skip_depth and data.strip():
            self.parts.append(data)


def clean_html(html: str, *, max_chars: int = 12000) -> str:
    """Strip a page to visible text + links (the model-facing content)."""
    p = _Cleaner()
    try:
        p.feed(html or "")
    except Exception:  # noqa: BLE001 -- malformed HTML should not crash extraction
        pass
    text = re.sub(r"[ \t]+", " ", "".join(p.parts))
    text = re.sub(r"\n\s*\n+", "\n", text).strip()
    return text[:max_chars]


# ---- deterministic extraction (rules; NO tokens) --------------------------

# Field -> label synonyms used to match <dl>/<table>/meta/JSON-LD keys.
_FIELD_SYNONYMS = {
    "name": ("name", "agency", "agency name", "company", "company name", "entity", "legal name", "title"),
    "license_no": ("license", "licence", "license no", "licence no", "license number", "poea",
                   "accreditation", "accreditation no", "permit no", "registration no", "reg no", "control no"),
    "status": ("status", "license status", "licence status", "validity", "standing", "state"),
    "address": ("address", "office address", "registered address", "location", "principal office"),
    "phone": ("phone", "telephone", "tel", "contact", "contact no", "contact number", "mobile", "landline"),
    "email": ("email", "e-mail", "e mail", "mail"),
    "website": ("website", "url", "web", "site", "homepage", "web site"),
    "representative": ("representative", "rep", "owner", "proprietor", "president", "contact person", "officer"),
    "classification": ("classification", "type", "category", "sector"),
    "expiry": ("expiry", "expiration", "valid until", "expiration date", "expires"),
}
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"(?:\+?\d[\d\-\s().]{6,}\d)")


class _PairExtractor(HTMLParser):
    """Capture label->value structure deterministically: <dl> dt/dd, two-cell
    <table> rows, <meta>, and <script type=application/ld+json> blocks."""

    def __init__(self) -> None:
        super().__init__()
        self.pairs: list[tuple[str, str]] = []
        self.meta: dict[str, str] = {}
        self.jsonld: list[str] = []
        self._mode: str | None = None
        self._buf: list[str] = []
        self._last_dt: str | None = None
        self._row: list[str] = []
        self._in_jsonld = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "script" and a.get("type", "").lower() == "application/ld+json":
            self._in_jsonld, self._buf = True, []
        elif tag == "meta":
            key = a.get("property") or a.get("name")
            if key and a.get("content"):
                self.meta.setdefault(key.lower(), a["content"])
        elif tag in ("dt", "dd", "th", "td"):
            self._mode, self._buf = tag, []
        elif tag == "tr":
            self._row = []

    def handle_endtag(self, tag):
        if tag == "script" and self._in_jsonld:
            self.jsonld.append("".join(self._buf))
            self._in_jsonld, self._buf = False, []
        elif tag in ("dt", "dd", "th", "td"):
            text = re.sub(r"\s+", " ", "".join(self._buf)).strip()
            if tag == "dt":
                self._last_dt = text
            elif tag == "dd" and self._last_dt:
                self.pairs.append((self._last_dt, text)); self._last_dt = None
            elif tag in ("th", "td"):
                self._row.append(text)
            self._mode, self._buf = None, []
        elif tag == "tr":
            if len(self._row) == 2 and self._row[0]:  # label | value row
                self.pairs.append((self._row[0], self._row[1]))
            self._row = []

    def handle_data(self, data):
        if self._in_jsonld or self._mode:
            self._buf.append(data)


def _flatten_jsonld(blocks: list[str]) -> dict:
    flat: dict[str, str] = {}
    for raw in blocks:
        try:
            data = json.loads(raw)
        except Exception:  # noqa: BLE001
            continue
        for obj in (data if isinstance(data, list) else [data]):
            if not isinstance(obj, dict):
                continue
            for k, v in obj.items():
                if isinstance(v, (str, int, float)):
                    flat.setdefault(k.lower(), str(v))
                elif isinstance(v, dict):  # nested, e.g. address/contactPoint
                    for k2, v2 in v.items():
                        if isinstance(v2, (str, int, float)):
                            flat.setdefault(k2.lower(), str(v2))
    return flat


def deterministic_extract(html: str, fields: list[str]) -> dict:
    """Rule-based extraction (NO model, NO tokens): JSON-LD > meta > dl/table
    label:value > typed regex (email/phone) > 'Label: value' text. Returns
    {extracted, methods, missing, found}."""
    p = _PairExtractor()
    try:
        p.feed(html or "")
    except Exception:  # noqa: BLE001
        pass
    labelmap: dict[str, str] = {}
    for lab, val in p.pairs:
        if lab and val:
            labelmap.setdefault(lab.strip().lower().rstrip(":").strip(), val.strip())
    for k, v in p.meta.items():
        labelmap.setdefault(k, v)
    jsonld = _flatten_jsonld(p.jsonld)
    text = clean_html(html, max_chars=20000)

    extracted, methods = {}, {}
    for f in fields:
        syns = _FIELD_SYNONYMS.get(f, (f.replace("_", " "),))
        val = method = None
        # 1) JSON-LD (most authoritative)
        for s in syns:
            sk = s.replace(" ", "")
            for k, v in jsonld.items():
                if sk and sk in k.replace(" ", "").replace("_", ""):
                    val, method = v, "json-ld"; break
            if val:
                break
        # 2) dl/table/meta label map (longest-synonym first for specificity)
        if not val:
            for s in sorted(syns, key=len, reverse=True):
                for k, v in labelmap.items():
                    if s in k:
                        val, method = v, "label"; break
                if val:
                    break
        # 3) typed pattern
        if not val and f in ("email", "e_mail"):
            m = _EMAIL_RE.search(text)
            if m:
                val, method = m.group(0), "regex"
        if not val and f in ("phone", "telephone", "contact", "contact_no", "mobile"):
            m = _PHONE_RE.search(text)
            if m:
                val, method = m.group(0).strip(), "regex"
        # 4) "Label: value" in visible text
        if not val:
            for s in sorted(syns, key=len, reverse=True):
                m = re.search(rf"\b{re.escape(s)}\s*[:\-]\s*([^\n|]{{2,80}})", text, re.I)
                if m:
                    val, method = m.group(1).strip(), "labeled-text"; break
        if val:
            extracted[f], methods[f] = val, method
    missing = [f for f in fields if f not in extracted]
    return {"extracted": extracted, "methods": methods, "missing": missing, "found": list(extracted)}


# ---- JSON parsing from a model reply --------------------------------------

def _parse_json(text: str) -> dict:
    if not text:
        return {}
    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(text[start:i + 1])
                        if isinstance(obj, dict):
                            return obj
                    except Exception:  # noqa: BLE001
                        break
        start = text.find("{", start + 1)
    return {}


# ---- LLM extraction (text + vision) ---------------------------------------

def llm_extract(content: str, fields: list[str], model_fn, *, instruction: str = "") -> dict:
    """Have the model extract `fields` from cleaned page `content` as JSON.
    `model_fn(prompt) -> text` is injectable."""
    flds = ", ".join(fields)
    prompt = (
        "You are extracting structured data from a web page. From the page CONTENT "
        f"below, extract these fields as a JSON object: {flds}. Use null for a field "
        "not present. Do not invent values. "
        f"{instruction}\n\n--- PAGE CONTENT ---\n{content}\n--- END ---\n"
        "Reply with ONE JSON object only.")
    return _parse_json(model_fn(prompt))


def vision_extract(image_b64: str, fields: list[str], vision_model_fn, *, instruction: str = "") -> dict:
    """Have a MULTIMODAL model extract `fields` from a page SCREENSHOT as JSON.
    `vision_model_fn(prompt, image_b64) -> text` is injectable."""
    flds = ", ".join(fields)
    prompt = ("Read this screenshot of a web page and extract these fields as a JSON "
              f"object: {flds}. Use null when not visible; do not invent. {instruction} "
              "Reply with ONE JSON object only.")
    return _parse_json(vision_model_fn(prompt, image_b64))


# ---- model_fn builders (Ollama / OpenAI-compatible) -----------------------

def _endpoint():
    base = os.environ.get("DUECARE_MODEL_BASE_URL") or os.environ.get("OLLAMA_HOST", "").rstrip("/")
    if base and not base.rstrip("/").endswith("/v1"):
        base = base.rstrip("/") + "/v1"
    key = os.environ.get("DUECARE_MODEL_API_KEY") or os.environ.get("OLLAMA_API_KEY") or ""
    model = os.environ.get("DUECARE_MODEL_NAME") or "gemma4:31b"
    return base, key, model


def text_model_fn():
    base, key, model = _endpoint()
    if not base:
        return None

    def call(prompt: str) -> str:
        body = json.dumps({"model": model, "temperature": 0.0, "stream": False,
                           "messages": [{"role": "user", "content": prompt}]}).encode("utf-8")
        req = urllib.request.Request(base.rstrip("/") + "/chat/completions", data=body,
                                     headers={"Content-Type": "application/json",
                                              "Authorization": f"Bearer {key}"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode("utf-8", "replace"))["choices"][0]["message"]["content"]
    return call


def vision_model_fn():
    base, key, model = _endpoint()
    if not base:
        return None

    def call(prompt: str, image_b64: str) -> str:
        content = [{"type": "text", "text": prompt},
                   {"type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{image_b64}"}}]
        body = json.dumps({"model": model, "temperature": 0.0, "stream": False,
                           "messages": [{"role": "user", "content": content}]}).encode("utf-8")
        req = urllib.request.Request(base.rstrip("/") + "/chat/completions", data=body,
                                     headers={"Content-Type": "application/json",
                                              "Authorization": f"Bearer {key}"})
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read().decode("utf-8", "replace"))["choices"][0]["message"]["content"]
    return call


# ---- live renderer (Playwright; reuses browser_scrape launcher) -----------

def _playwright_render_page(url: str, *, screenshot: bool = True, nav_timeout_s: float = 30.0) -> dict:
    bs = _sibling("browser_scrape")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # noqa: BLE001
        raise ImportError("Playwright required: pip install playwright && "
                          "python -m playwright install chromium") from exc
    with sync_playwright() as pw:
        browser = bs._launch_browser(pw)
        page = browser.new_context(user_agent=bs.USER_AGENT).new_page()
        page.goto(url, timeout=int(nav_timeout_s * 1000), wait_until="domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=int(nav_timeout_s * 1000))
        except Exception:  # noqa: BLE001
            pass
        out = {"url": page.url, "title": page.title(), "html": page.content(), "screenshot_b64": ""}
        if screenshot:
            try:
                out["screenshot_b64"] = base64.b64encode(page.screenshot(full_page=True)).decode("ascii")
            except Exception:  # noqa: BLE001
                pass
        browser.close()
    return out


def scrape_page(url: str, fields: list[str], *, renderer=None, model_fn=None,
                vision_model_fn=None, want_screenshot: bool = False, tier: str = "auto") -> dict:
    """Render `url` then extract `fields` in a robustness waterfall:
      tier 1 DETERMINISTIC -- rule-based HTML parse (NO tokens), always run;
      tier 2 LLM           -- only for fields the rules missed (tier 'auto') or
                              all fields (tier 'llm'); costs tokens;
      tier 3 VISION        -- screenshot -> multimodal model for anything still
                              missing (skipped when tier='deterministic').
    `tier`: 'deterministic' (free, rules only) | 'auto' (rules + LLM gap-fill) |
    'llm' (rules + LLM all). renderer/model callables injectable for tests."""
    render = renderer or (lambda u: _playwright_render_page(u, screenshot=want_screenshot))
    page = render(url)
    html = page.get("html", "")
    content = clean_html(html) or page.get("text", "")
    result = {"url": page.get("url", url), "title": page.get("title", ""), "fields": fields,
              "tier": tier, "n_content_chars": len(content)}

    det = deterministic_extract(html, fields)
    result["deterministic"] = det["extracted"]
    result["methods"] = det["methods"]
    merged = dict(det["extracted"])
    used_llm = False

    if model_fn is not None and tier in ("auto", "llm"):
        targets = det["missing"] if tier == "auto" else fields
        if targets:
            llm = llm_extract(content, targets, model_fn)
            used_llm = True
            result["llm_extracted"] = {k: v for k, v in llm.items() if v not in (None, "")}
            for k in targets:
                if merged.get(k) in (None, "") and llm.get(k) not in (None, ""):
                    merged[k] = llm[k]

    if vision_model_fn is not None and tier != "deterministic" and page.get("screenshot_b64"):
        vis = vision_extract(page["screenshot_b64"], fields, vision_model_fn)
        used_llm = True
        result["vision_extracted"] = vis
        for k in fields:
            if merged.get(k) in (None, "") and vis.get(k) not in (None, ""):
                merged[k] = vis[k]

    result["extracted"] = merged
    result["tokens_used"] = used_llm
    result["n_deterministic"] = len(det["extracted"])
    result["_screenshot_b64"] = page.get("screenshot_b64", "")
    return result


# ---- CLI -------------------------------------------------------------------

def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (s or "").lower()).strip("_")[:60] or "page"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", required=True)
    ap.add_argument("--fields", default="name,license_no,status,address,phone,email",
                    help="comma-separated fields to extract")
    ap.add_argument("--tier", default="auto", choices=["deterministic", "auto", "llm"],
                    help="deterministic=rules only (no tokens); auto=rules+LLM gap-fill; llm=rules+LLM all")
    ap.add_argument("--screenshot", action="store_true", help="also capture + vision-extract")
    ap.add_argument("--out", default="")
    args = ap.parse_args(argv)

    fields = [f.strip() for f in args.fields.split(",") if f.strip()]
    # the deterministic tier needs no model; only build the endpoint for auto/llm
    mf = text_model_fn() if args.tier in ("auto", "llm") else None
    vf = vision_model_fn() if (args.screenshot and args.tier != "deterministic") else None
    if mf is None and args.tier in ("auto", "llm"):
        print("no model endpoint (set OLLAMA_HOST/_API_KEY or DUECARE_MODEL_BASE_URL); "
              "falling back to deterministic rules only.", file=sys.stderr)

    try:
        res = scrape_page(args.url, fields, model_fn=mf, vision_model_fn=vf,
                          want_screenshot=args.screenshot, tier=args.tier)
    except ImportError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    out_dir = _ROOT / "reports" / "llm_scrape"
    out_dir.mkdir(parents=True, exist_ok=True)
    shot = res.pop("_screenshot_b64", "")
    if shot:
        png = out_dir / f"{_slug(args.url)}.png"
        png.write_bytes(base64.b64decode(shot))
        res["screenshot_path"] = str(png)
    out = Path(args.out) if args.out else (out_dir / f"{_slug(args.url)}.json")
    out.write_text(json.dumps({"_synthetic": False, **res}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"title: {res.get('title','')[:70]}", file=sys.stderr)
    print(f"tier={res.get('tier')} tokens_used={res.get('tokens_used')} "
          f"deterministic={res.get('n_deterministic')}/{len(fields)} fields", file=sys.stderr)
    print(f"  deterministic ({res.get('methods')}): {res.get('deterministic')}", file=sys.stderr)
    if "llm_extracted" in res:
        print(f"  llm gap-fill: {res.get('llm_extracted')}", file=sys.stderr)
    if "vision_extracted" in res:
        print(f"  vision: {res.get('vision_extracted')}", file=sys.stderr)
    print(f"MERGED: {res.get('extracted')}", file=sys.stderr)
    print(f"-> {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
