"""Correctness and performance coverage for harness fuzzy matching."""
from __future__ import annotations

import importlib
import random
import sys
import time
import types
from pathlib import Path

import pytest


def _load_harness():
    pkg_root = Path(__file__).parent.parent / "src"
    if str(pkg_root) not in sys.path:
        sys.path.insert(0, str(pkg_root))
    if "duecare" not in sys.modules:
        duecare = types.ModuleType("duecare")
        duecare.__path__ = [str(pkg_root / "duecare")]
        sys.modules["duecare"] = duecare
    if "duecare.chat" not in sys.modules:
        duecare_chat = types.ModuleType("duecare.chat")
        duecare_chat.__path__ = [str(pkg_root / "duecare" / "chat")]
        sys.modules["duecare.chat"] = duecare_chat
    return importlib.import_module("duecare.chat.harness")


def _levenshtein_similarity(left: str, right: str) -> float:
    if left == right:
        return 1.0
    if not left or not right:
        return 0.0
    previous = list(range(len(left) + 1))
    for row, right_char in enumerate(right, 1):
        current = [row]
        for column, left_char in enumerate(left, 1):
            current.append(min(
                current[column - 1] + 1,
                previous[column] + 1,
                previous[column - 1] + (left_char != right_char),
            ))
        previous = current
    return 1.0 - (previous[-1] / max(len(left), len(right)))


def _brute_force_fuzzy_match(
    needle: str,
    haystack: str,
    *,
    threshold: float = 0.80,
) -> bool:
    needle = needle.lower()
    haystack = haystack.lower()
    n = len(needle)
    if n == 0:
        return False
    step = 1 if n <= 16 else max(1, n // 8)
    for window_len in (n, n - 1, n + 1):
        if window_len <= 0 or (window_len != n and window_len > len(haystack)):
            continue
        for start in range(0, max(1, len(haystack) - window_len + 1), step):
            window = haystack[start:start + window_len]
            if _levenshtein_similarity(needle, window) >= threshold:
                return True
    return False


@pytest.mark.parametrize("seed", range(8))
def test_fuzzy_match_has_randomized_brute_force_parity(seed: int) -> None:
    """Candidate pruning preserves the prior n/n-1/n+1 scan result."""
    harness = _load_harness()
    rng = random.Random(20_260_714 + seed)
    alphabet = "abcde "
    for _ in range(100):
        needle = "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 24)))
        haystack = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 40)))
        expected = _brute_force_fuzzy_match(needle, haystack)
        assert harness._fuzzy_substring_match(needle, haystack) is expected, (
            seed,
            needle,
            haystack,
        )


def test_fuzzy_match_prunes_unrelated_8kb_haystack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unrelated long response should not launch thousands of DPs."""
    harness = _load_harness()
    haystack = (
        "The quick brown fox reviews statutory safeguards and documented evidence. "
        * 120
    )[:8_192]
    needle = "qzxwkvjphrmbtycf"
    calls = 0
    original = harness._normalized_edit_distance

    def counted_distance(left: str, right: str) -> float:
        nonlocal calls
        calls += 1
        return original(left, right)

    monkeypatch.setattr(harness, "_normalized_edit_distance", counted_distance)
    started = time.perf_counter()
    assert not harness._fuzzy_substring_match(needle, haystack)
    elapsed = time.perf_counter() - started

    assert calls == 0
    assert elapsed < 0.5
