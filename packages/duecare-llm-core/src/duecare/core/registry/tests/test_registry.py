"""Real tests for duecare.core.registry.Registry."""

from __future__ import annotations

import pytest

from duecare.core.registry import Registry


def test_register_and_get_class() -> None:
    r: Registry = Registry(kind="test_plugin")

    @r.register("alpha", note="first")
    class Alpha:
        pass

    @r.register("beta")
    class Beta:
        pass

    assert r.has("alpha")
    assert r.has("beta")
    assert not r.has("gamma")
    assert r.get("alpha") is Alpha
    assert r.get("beta") is Beta
    assert r.all_ids() == ["alpha", "beta"]
    assert r.metadata("alpha") == {"note": "first"}
    assert len(r) == 2
    assert "alpha" in r


def test_register_and_get_instance_via_add() -> None:
    r: Registry = Registry(kind="model")

    class M:
        def __init__(self, name: str) -> None:
            self.name = name

    m = M("gemma")
    r.add("gemma_4_e4b", m, provider="transformers")

    assert r.has("gemma_4_e4b")
    assert r.get("gemma_4_e4b") is m
    assert r.metadata("gemma_4_e4b") == {"provider": "transformers"}


def test_double_register_raises() -> None:
    r: Registry = Registry(kind="t")

    @r.register("alpha")
    class A1:
        pass

    with pytest.raises(ValueError, match="is already registered"):
        @r.register("alpha")
        class A2:  # noqa: F811
            pass


def test_unknown_id_raises_keyerror() -> None:
    r: Registry = Registry(kind="t")
    with pytest.raises(KeyError, match="Unknown t id 'missing'"):
        r.get("missing")


def test_empty_registry_shows_empty_in_error() -> None:
    r: Registry = Registry(kind="empty")
    with pytest.raises(KeyError, match=r"Known: \(empty\)"):
        r.get("x")


def test_iteration_preserves_sorted_order() -> None:
    r: Registry = Registry(kind="t")
    for id in ["zeta", "alpha", "gamma", "beta"]:
        r.add(id, object())
    ids = [i for i, _ in r.items()]
    assert ids == ["alpha", "beta", "gamma", "zeta"]


def test_repr_includes_kind_and_count() -> None:
    r: Registry = Registry(kind="model")
    r.add("gemma", object())
    r.add("qwen", object())
    assert repr(r) == "Registry[model](2 entries)"


def test_metadata_defaults_to_empty_dict() -> None:
    r: Registry = Registry(kind="t")

    @r.register("x")
    class X:
        pass

    assert r.metadata("x") == {}
    assert r.metadata("nonexistent") == {}
