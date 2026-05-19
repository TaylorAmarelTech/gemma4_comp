from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KERNEL_DIR = ROOT / "kaggle" / "03-universal-llm-benchmark"


def test_universal_benchmark_kernel_contract():
    kernel = (KERNEL_DIR / "kernel.py").read_text(encoding="utf-8")
    readme = (KERNEL_DIR / "README.md").read_text(encoding="utf-8")
    metadata = (KERNEL_DIR / "kernel-metadata.json").read_text(encoding="utf-8")

    assert "DueCare Universal LLM Benchmark" in kernel
    assert "discover_catalog" in kernel
    assert "harnesses" in kernel
    assert "test_file_count" in kernel
    assert "call_target" in kernel
    assert "openai_compatible" in kernel
    assert "anthropic_messages" in kernel
    assert "raw_http" in kernel
    assert "claude-opus-4-7" in kernel
    assert "deterministic_fallback" in kernel
    assert "results.json" in kernel
    assert "calls.jsonl" in kernel

    assert "optional evaluation surface" in readme
    assert "Claude Opus" in readme
    assert "raw_http" in readme
    assert "duecare-universal-llm-benchmark" in metadata


def test_universal_benchmark_kernel_is_not_primary_path():
    index = (ROOT / "kaggle" / "_INDEX.md").read_text(encoding="utf-8")
    assert "Active Submission Path" in index
    assert "Optional Evaluation Surface" in index
    assert "03-universal-llm-benchmark" in index
