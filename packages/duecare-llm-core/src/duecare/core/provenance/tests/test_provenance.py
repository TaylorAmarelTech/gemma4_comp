"""Real tests for duecare.core.provenance."""

from __future__ import annotations

from typing import Any

import re

from duecare.core.provenance import (
    compute_checksum,
    generate_run_id,
    get_git_sha,
    get_short_sha,
    hash_config,
    simhash,
)


class TestRunId:
    def test_run_id_format(self) -> None:
        run_id = generate_run_id("evaluate_only")
        # format: YYYYMMDDHHMMSSffffff_{sha}_{workflow_id}
        # 14-digit date + 6-digit microsecond = 20 digits total
        pattern = r"^\d{20}_[a-z0-9]{7,8}_evaluate_only$"
        assert re.match(pattern, run_id), f"Unexpected format: {run_id}"

    def test_run_id_is_unique_per_call(self) -> None:
        # Microsecond precision should make back-to-back calls unique
        a = generate_run_id("wf")
        b = generate_run_id("wf")
        assert a != b, f"Back-to-back run_ids should differ: {a} vs {b}"
        assert len(a) > 20
        assert len(b) > 20

    def test_workflow_id_with_slash_is_sanitized(self) -> None:
        run_id = generate_run_id("path/with/slashes")
        assert "/" not in run_id
        assert "path_with_slashes" in run_id

    def test_workflow_id_with_spaces_is_sanitized(self) -> None:
        run_id = generate_run_id("name with spaces")
        assert " " not in run_id
        assert "name_with_spaces" in run_id


class TestGitSha:
    def test_get_git_sha_returns_string(self) -> None:
        sha = get_git_sha()
        assert isinstance(sha, str)
        assert len(sha) > 0

    def test_get_short_sha_length(self) -> None:
        short = get_short_sha(8)
        assert len(short) in (7, 8)  # 'unknown' (7) or real sha (8)


class TestHashing:
    def test_compute_checksum_stable(self) -> None:
        assert compute_checksum("hello") == compute_checksum("hello")
        assert compute_checksum("hello") != compute_checksum("world")

    def test_compute_checksum_accepts_bytes(self) -> None:
        assert compute_checksum(b"hello") == compute_checksum("hello")

    def test_compute_checksum_returns_hex_string(self) -> None:
        h = compute_checksum("x")
        assert len(h) == 64  # sha256 hex
        assert all(c in "0123456789abcdef" for c in h)

    def test_hash_config_is_order_invariant_for_dicts(self) -> None:
        a = hash_config({"a": 1, "b": 2})
        b = hash_config({"b": 2, "a": 1})
        assert a == b

    def test_hash_config_accepts_nested_structures(self) -> None:
        h = hash_config({"nested": {"list": [1, 2, 3], "val": "x"}})
        assert len(h) == 64

    def test_hash_config_differs_for_different_input(self) -> None:
        assert hash_config({"a": 1}) != hash_config({"a": 2})


class TestSimHash:
    def test_simhash_deterministic(self) -> None:
        a = simhash("the quick brown fox")
        b = simhash("the quick brown fox")
        assert a == b

    def test_simhash_empty_text(self) -> None:
        assert simhash("") == 0

    def test_simhash_near_duplicates_collide_more_than_unrelated(self) -> Any:
        h_near_a = simhash("the quick brown fox jumps over the lazy dog")
        h_near_b = simhash("the quick brown fox leaps over the lazy dog")
        h_unrelated = simhash("completely unrelated financial obfuscation scheme")

        # Hamming distance: lower = more similar
        def hamming(x: int, y: int) -> int:
            return bin(x ^ y).count("1")

        near_distance = hamming(h_near_a, h_near_b)
        unrelated_distance = hamming(h_near_a, h_unrelated)
        assert near_distance < unrelated_distance

    def test_simhash_returns_int_in_64bit_range(self) -> None:
        h = simhash("test")
        assert isinstance(h, int)
        assert 0 <= h < 2**64
