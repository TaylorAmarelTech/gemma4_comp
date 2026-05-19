from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KERNEL_DIR = ROOT / "kaggle" / "04-kaggle-community-benchmark"


def test_kaggle_community_benchmark_kernel_contract():
    kernel = (KERNEL_DIR / "kernel.py").read_text(encoding="utf-8")
    readme = (KERNEL_DIR / "README.md").read_text(encoding="utf-8")
    metadata = (KERNEL_DIR / "kernel-metadata.json").read_text(encoding="utf-8")

    assert "DueCare Kaggle Community Benchmark" in kernel
    assert "kaggle_benchmarks" in kernel
    assert "@kbench.task" in kernel
    assert "duecare_single_safety_row" in kernel
    assert "store_task=False" in kernel
    assert "duecare_migrant_worker_safety_benchmark" in kernel
    assert "kbench.llm" in kernel
    assert "kbench.llms" in kernel
    assert "DUECARE_KBENCH_JUDGE_MODEL" in kernel
    assert "anthropic/claude-opus-4" in kernel
    assert "deterministic_score" in kernel
    assert "kbench.assertions.assert_false" in kernel
    assert "kbench.assertions.assert_true" in kernel
    assert "assess_response_with_judge" in kernel
    assert "duecare.kaggle_community_benchmark.v1" in kernel

    assert "benchmark-publishing surface" in readme
    assert "Kaggle's AI model quota" in readme
    assert "kaggle_benchmarks" in readme
    assert "duecare-kaggle-community-benchmark" in metadata


def test_optional_benchmark_indexes_include_kaggle_community_surface():
    index = (ROOT / "kaggle" / "_INDEX.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    guide = (ROOT / "docs" / "notebook_guide.md").read_text(encoding="utf-8")

    assert "03-universal-llm-benchmark" in index
    assert "04-kaggle-community-benchmark" in index
    assert "04-kaggle-community-benchmark" in readme
    assert "04-kaggle-community-benchmark" in guide
    assert "primary recording path" in readme
