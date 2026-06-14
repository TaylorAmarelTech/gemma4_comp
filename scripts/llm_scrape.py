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
                vision_model_fn=None, want_screenshot: bool = False) -> dict:
    """Render `url`, clean its HTML, and extract `fields` with the LLM (text) and
    optionally vision. renderer/model callables injectable for tests."""
    render = renderer or (lambda u: _playwright_render_page(u, screenshot=want_screenshot))
    page = render(url)
    content = clean_html(page.get("html", "")) or page.get("text", "")
    result = {"url": page.get("url", url), "title": page.get("title", ""),
              "fields": fields, "n_content_chars": len(content)}
    if model_fn is not None:
        result["extracted"] = llm_extract(content, fields, model_fn)
    if vision_model_fn is not None and page.get("screenshot_b64"):
        result["vision_extracted"] = vision_extract(page["screenshot_b64"], fields, vision_model_fn)
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
    ap.add_argument("--screenshot", action="store_true", help="also capture + vision-extract")
    ap.add_argument("--out", default="")
    args = ap.parse_args(argv)

    fields = [f.strip() for f in args.fields.split(",") if f.strip()]
    mf = text_model_fn()
    vf = vision_model_fn() if args.screenshot else None
    if mf is None:
        print("no model endpoint (set OLLAMA_HOST/_API_KEY or DUECARE_MODEL_BASE_URL); "
              "rendering + cleaning only.", file=sys.stderr)

    try:
        res = scrape_page(args.url, fields, model_fn=mf, vision_model_fn=vf,
                          want_screenshot=args.screenshot)
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
    print(f"text extract: {res.get('extracted')}", file=sys.stderr)
    if "vision_extracted" in res:
        print(f"vision extract: {res.get('vision_extracted')}", file=sys.stderr)
    print(f"-> {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
