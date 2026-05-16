"""Local fake-Gemma workbench server for browser tests.

This server keeps Playwright flows deterministic on developer machines:
it marks a model as loaded, returns short Gemma-like text, and wires a
local search backend so no external network call is required.
"""

from __future__ import annotations

import os

import uvicorn

from duecare.chat import create_app


def fake_gemma(messages, **kwargs):  # noqa: ANN001, ANN003
    text = ""
    try:
        last = messages[-1]
        content = last.get("content", "")
        if isinstance(content, list):
            text = " ".join(
                str(part.get("text", ""))
                for part in content
                if isinstance(part, dict)
            )
        else:
            text = str(content)
    except Exception:
        text = ""
    if "JSON" in text or "knowledge" in text.lower():
        return (
            '{"schema_version":"1.0","knowledge_object_type":"context_snippet",'
            '"id":"local-fake-draft","version":"v1-draft",'
            '"content":{"content":"Local fake Gemma draft for browser testing."},'
            '"extensions":{"draft":true,"needs_review":true}}'
        )
    return (
        "Local fake Gemma response. Indicators: fee camouflage, debt bondage, "
        "jurisdiction shopping. Citations should be verified by the harness."
    )


def fake_search(query: str, top_n: int = 5) -> dict:
    base = [
        {
            "title": "Two persons and company convicted of operating employment agency",
            "url": "https://www.info.gov.hk/gia/general/202404/29/P2024042900518.htm",
            "snippet": "Hong Kong Labour Department prosecution under Employment Ordinance Part XII.",
        },
        {
            "title": "Man fined for operating unlicensed employment agency",
            "url": "https://www.info.gov.hk/gia/general/202411/04/example.htm",
            "snippet": "A person was fined for operating an employment agency without a valid licence.",
        },
        {
            "title": "Employment Agency Regulations commission cap reminder",
            "url": "https://www.eaa.labour.gov.hk/en/home.html",
            "snippet": "Employment agencies must comply with statutory fee and licensing rules.",
        },
        {
            "title": "POEA zero placement fee reminder for Hong Kong domestic work",
            "url": "https://www.dmw.gov.ph/example-zero-fee",
            "snippet": "Recruitment agencies must not charge prohibited placement fees to workers.",
        },
        {
            "title": "ILO fair recruitment guidance",
            "url": "https://www.ilo.org/global/topics/fair-recruitment",
            "snippet": "Workers should not bear recruitment fees or related costs.",
        },
    ]
    return {
        "results": [
            {"rank": i + 1, **item}
            for i, item in enumerate(base[: max(1, min(int(top_n), len(base)))])
        ],
        "source": "local-fake-search",
        "elapsed_ms": 1,
        "query": query,
    }


app = create_app(
    gemma_call=fake_gemma,
    online_search_call=fake_search,
    model_info={
        "loaded": True,
        "name": "gemma-4-local-fake",
        "display": "Gemma 4 local fake",
        "device": "cpu",
    },
)


@app.get("/api/load-model/status")
def load_model_status() -> dict:
    return {
        "status": "ready",
        "phase": "ready",
        "variant": "e4b-it",
        "active_model": "gemma-4-local-fake",
        "logs": [
            {
                "ts": "local",
                "phase": "ready",
                "severity": "info",
                "message": "Local fake model is already loaded for browser tests.",
            }
        ],
        "variants": [
            {"key": "e2b-it", "name": "Gemma 4 E2B-it"},
            {"key": "e4b-it", "name": "Gemma 4 E4B-it"},
        ],
    }


@app.get("/api/load-model/logs")
def load_model_logs() -> dict:
    return {
        "events": [
            {
                "ts": "local",
                "phase": "ready",
                "severity": "info",
                "message": "Local fake model is already loaded for browser tests.",
            }
        ]
    }


@app.post("/api/load-model")
def load_model() -> dict:
    return {"status": "ready", "variant": "e4b-it", "message": "local fake model ready"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8811"))
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
