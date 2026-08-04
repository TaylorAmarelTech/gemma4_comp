"""Regenerate the canonical `<!-- duecare:kernel-footer -->` block in every
judge-facing Kaggle README so the roster reflects all 27 kernels (3 core + 24
appendix), with the current kernel bolded as "You are here".

Idempotent: runs as a text rewrite, no validators are invoked.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple


class Kernel(NamedTuple):
    key: str
    folder: str
    label: str

    @property
    def display_line(self) -> str:
        return f"[#{self.key} {self._tier()}: {self.label}](../{self.folder}/README.md)"

    @property
    def header_label(self) -> str:
        return f"#{self.key} {self._tier()} — {self.label}"

    def _tier(self) -> str:
        return "core" if self.key in {"01", "02", "03"} else "appendix"


ROSTER: tuple[Kernel, ...] = (
    Kernel("01", "01-duecare-exploration-workbench", "Migrant-worker safety playground"),
    Kernel("02", "02-live-demo", "Live demo (focused walkthrough)"),
    Kernel("03", "03-duecare-video-pitch", "Video pitch (in-app slides + presenter remote)"),
    Kernel("A01", "A-01-chat-playground", "Stock Gemma 4 chat baseline"),
    Kernel("A02", "A-02-chat-playground-with-grep-rag-tools", "Harness ablation runner"),
    Kernel("A03", "A-03-content-classification-playground", "Hands-on classification sandbox"),
    Kernel("A04", "A-04-content-knowledge-builder-playground", "Knowledge-builder sandbox + JSON export"),
    Kernel("A05", "A-05-gemma-content-classification-evaluation", "NGO classifier evaluation dashboard"),
    Kernel("A06", "A-06-prompt-generation", "Two-track synthetic data generator"),
    Kernel("A07", "A-07-bench-and-tune", "Adapter training + new-model benchmark"),
    Kernel("A08", "A-08-research-graphs", "Research graphs (CPU-only)"),
    Kernel("A09", "A-09-chat-playground-with-agentic-research", "Agentic-research chat (BYOK + Playwright)"),
    Kernel("A10", "A-10-runtime-vs-weights-safety-study", "Jailbroken-Gemma comparison"),
    Kernel("A11", "A-11-grading-evaluation", "Runtime harness-lift regenerator"),
    Kernel("A12", "A-12-pii-fine-tune-eval", "PrivacyRedactor LoRA fine-tune + eval"),
    Kernel("A13", "A-13-multimodal-document-analyzer", "Multimodal document analyzer (Gemma 4 vision)"),
    Kernel("A14", "A-14-on-device-export", "On-device export (LoRA merge -> GGUF + LiteRT)"),
    Kernel("A15", "A-15-ugc-batch-moderator", "UGC batch moderator (Lane 01 platform safety)"),
    Kernel("A16", "A-16-ngo-local-kb", "NGO local-KB / case-file ingestion"),
    Kernel("A17", "A-17-knowledge-pack-builder", "Knowledge-pack builder + verifier"),
    Kernel("A18", "A-18-sentinel-research-monitor", "Sentinel / research monitor"),
    Kernel("A19", "A-19-multilingual-demo", "Multilingual demo (5-language playback)"),
    Kernel("A20", "A-20-privacy-boundary", "Privacy boundary visualization"),
    Kernel("A21", "A-21-long-context-demo", "Long-context demo (Gemma 4 128K)"),
    Kernel("A22", "A-22-streaming-demo", "Token streaming demo (Gemma 4 SSE)"),
    Kernel("A23", "A-23-coordinator-demo", "Coordinator demo (Gemma 4 native function calling)"),
    Kernel("A24", "A-24-demo-replay", "Demo replay (zero-inference video kernel)"),
)

FOLDER_TO_KERNEL: dict[str, Kernel] = {k.folder: k for k in ROSTER}

FOOTER_OPEN = "<!-- duecare:kernel-footer -->"


def build_footer(current: Kernel) -> str:
    lines: list[str] = []
    lines.append(FOOTER_OPEN)
    lines.append("")
    lines.append("### All DueCare kernels")
    lines.append("")
    lines.append(f"You are here: **{current.header_label}**.")
    lines.append("")
    for k in ROSTER:
        line = "- " + k.display_line
        if k.key == current.key:
            line = f"- **{k.display_line}**"
        lines.append(line)
    lines.append("")
    lines.append("Index page: [`kaggle/_INDEX.md`](../_INDEX.md).")
    return "\n".join(lines) + "\n"


FOOTER_BLOCK_RE = re.compile(
    r"(?ms)^<!-- duecare:kernel-footer -->\n.*?Index page: \[`kaggle/_INDEX\.md`\]\(\.\./_INDEX\.md\)\.\n"
)


def rewrite(readme: Path, kernel: Kernel) -> str:
    text = readme.read_text(encoding="utf-8")
    block = build_footer(kernel)
    if FOOTER_BLOCK_RE.search(text):
        new_text = FOOTER_BLOCK_RE.sub(block, text, count=1)
        action = "replaced"
    else:
        body = text.rstrip() + "\n"
        sep = "\n---\n\n"
        new_text = body + sep + block
        action = "appended"
    if new_text == text:
        return "unchanged"
    readme.write_text(new_text, encoding="utf-8")
    return action


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    kaggle_dir = root / "kaggle"
    summary: list[str] = []
    for folder, kernel in FOLDER_TO_KERNEL.items():
        readme = kaggle_dir / folder / "README.md"
        if not readme.exists():
            summary.append(f"  missing: {folder}/README.md")
            continue
        result = rewrite(readme, kernel)
        summary.append(f"  {result}: {folder}")
    print("Kernel footer refresh:")
    for line in summary:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
