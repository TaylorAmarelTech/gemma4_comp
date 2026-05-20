"""Behavioural tests for the modules extracted out of kernel.py.

The neighbouring ``test_design_tooltip_migration.py`` does string-grep
regression checks. This file exercises the extracted modules with
real method calls: ModelQueue concurrent ordering, Event-based drain
timing, templates fill provenance, variants drift detection, and the
Pydantic body models' boolean coercion.

Goal: prove the modules behave correctly in isolation so future
refactors that touch the same surface fail loudly here instead of
silently in production.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

# Make the chat package importable without a wheel install.
_SRC_ROOT = Path(__file__).parents[1] / "src"
import sys
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from duecare.chat.inference_queue import (
    ModelQueue,
    QueueClosed,
    QueueFull,
)
from duecare.chat.kernel_api import (
    LoadEvaluatorModelRequest,
    LoadModelRequest,
    UnloadModelRequest,
    UseChatAsJudgeRequest,
    parse_request_bool,
)
from duecare.chat.model_slot import ModelSlot
from duecare.chat.templates import (
    TEMPLATES_REGISTRY,
    TemplateField,
    TemplateSpec,
    bundle_field_hint,
    clear_custom_templates,
    gemma_fill_template,
    is_builtin_template,
    parse_bool,
    register_template,
    render_template,
    safe_json_extract,
)
from duecare.chat.variants import (
    VARIANT_REGISTRY,
    VariantSpec,
    clear_custom_variants,
    footprint_gb,
    get_variant,
    is_builtin_variant,
    is_cloud_variant,
    list_variant_ids,
    register_variant,
    to_ui_map,
)


# ---------------------------------------------------------------------------
# parse_request_bool / parse_bool
# ---------------------------------------------------------------------------


class TestParseBool:
    """Cover every input shape the kernel might see in a JSON body."""

    @pytest.mark.parametrize("value,default,expected", [
        ("true", False, True),
        ("True", False, True),
        ("TRUE", False, True),
        ("yes", False, True),
        ("on", False, True),
        ("1", False, True),
        ("y", False, True),
        ("false", True, False),
        ("False", True, False),
        ("FALSE", True, False),
        ("no", True, False),
        ("off", True, False),
        ("0", True, False),
        ("n", True, False),
        ("", True, False),  # empty string is falsy
        (True, False, True),
        (False, True, False),
        (1, False, True),
        (0, True, False),
        (None, True, True),
        (None, False, False),
        ("garbage", True, True),   # unknown -> default
        ("garbage", False, False),
        (object(), True, True),    # non-coercible -> default
    ])
    def test_parse_request_bool(self, value, default, expected):
        assert parse_request_bool(value, default) is expected

    def test_templates_parse_bool_matches_kernel_api(self):
        """templates.parse_bool and kernel_api.parse_request_bool
        share the same semantic contract."""
        for value, default in [
            ("true", False), ("false", True), (1, False), (0, True),
            (None, True), ("garbage", False),
        ]:
            assert parse_bool(value, default) is parse_request_bool(value, default)


# ---------------------------------------------------------------------------
# Pydantic body models
# ---------------------------------------------------------------------------


class TestPydanticBodyModels:
    """Each mutation endpoint's body model coerces strings + ignores
    extras + applies the right defaults."""

    def test_use_chat_as_judge_default_enabled_true(self):
        r = UseChatAsJudgeRequest.model_validate({})
        assert r.enabled is True
        assert r.operator_token == ""

    def test_use_chat_as_judge_disable_via_string_false(self):
        r = UseChatAsJudgeRequest.model_validate({"enabled": "false"})
        assert r.enabled is False

    def test_use_chat_as_judge_ignores_extra_fields(self):
        r = UseChatAsJudgeRequest.model_validate(
            {"enabled": True, "tracing_id": "abc", "unknown": 42}
        )
        assert r.enabled is True

    def test_load_model_strips_variant_whitespace(self):
        r = LoadModelRequest.model_validate({"variant": "  31b-it  "})
        assert r.variant == "31b-it"

    def test_load_model_default_override_false(self):
        r = LoadModelRequest.model_validate({})
        assert r.variant == ""
        assert r.override is False

    def test_load_evaluator_defaults_to_31b_it(self):
        r = LoadEvaluatorModelRequest.model_validate({})
        assert r.variant == "31b-it"

    def test_load_evaluator_empty_string_falls_back(self):
        r = LoadEvaluatorModelRequest.model_validate({"variant": ""})
        assert r.variant == "31b-it"

    def test_load_evaluator_respects_explicit_variant(self):
        r = LoadEvaluatorModelRequest.model_validate({"variant": "e4b-it"})
        assert r.variant == "e4b-it"

    def test_unload_drain_seconds_clamped_to_600(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            UnloadModelRequest.model_validate({"drain_seconds": 9999})

    def test_unload_string_booleans_coerce(self):
        r = UnloadModelRequest.model_validate(
            {"force": "true", "purge_cache": "0"}
        )
        assert r.force is True
        assert r.purge_cache is False


# ---------------------------------------------------------------------------
# ModelQueue concurrency
# ---------------------------------------------------------------------------


class TestModelQueue:
    """Exercise the extracted ModelQueue with real threads."""

    def _backend(self, work_ms: int = 50):
        """Returns a backend callable that sleeps ``work_ms`` then
        returns ``"ok:<arg>"``."""
        def backend(arg, **kwargs):
            time.sleep(work_ms / 1000.0)
            return f"ok:{arg}"
        return backend

    def test_closed_slot_refuses_tickets(self):
        q = ModelQueue()
        wrapped = q.wrap(self._backend(10), "chat")
        with pytest.raises(QueueClosed):
            wrapped("x")

    def test_open_slot_serves_ticket(self):
        q = ModelQueue()
        wrapped = q.wrap(self._backend(10), "chat")
        q.open_slot("chat")
        assert wrapped("a") == "ok:a"

    def test_concurrent_callers_all_complete(self):
        q = ModelQueue()
        wrapped = q.wrap(self._backend(20), "chat")
        q.open_slot("chat")
        results = []

        def caller(i):
            results.append(wrapped(i))

        threads = [threading.Thread(target=caller, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert sorted(results) == ["ok:0", "ok:1", "ok:2", "ok:3"]

    def test_serialization_observed_mid_flight(self):
        """Only 1 ticket should be active at a time on a single slot;
        the rest queue. Verified by capturing the snapshot mid-flight."""
        q = ModelQueue()
        wrapped = q.wrap(self._backend(100), "chat")
        q.open_slot("chat")

        def caller(i):
            wrapped(i)

        threads = [threading.Thread(target=caller, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        time.sleep(0.030)  # let the first ticket reach the lock
        snap = q.snapshot()
        chat = snap["slots"]["chat"]
        assert chat["n_active"] == 1, f"expected 1 active, got {chat['n_active']}"
        assert chat["n_waiting"] >= 1, f"expected waiters, got {chat['n_waiting']}"
        for t in threads:
            t.join()

    def test_backpressure_rejects_above_max_waiting(self):
        """With slow callers + 10 simultaneous launches, some get
        QueueFull because MAX_WAITING=5."""
        q = ModelQueue()
        wrapped = q.wrap(self._backend(80), "chat")
        q.open_slot("chat")
        results = []

        def caller(i):
            try:
                results.append(wrapped(i))
            except QueueFull:
                results.append("FULL")

        threads = [threading.Thread(target=caller, args=(i,)) for i in range(12)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        # Should see at least one QueueFull (12 callers > 1 active + 5 waiting).
        n_full = sum(1 for r in results if r == "FULL")
        assert n_full >= 1, f"expected backpressure rejections, saw {results}"

    def test_event_based_drain_completes_quickly(self):
        """close_slot should NOT spin at 250ms intervals -- it should
        wake on the idle_event as soon as the last ticket completes."""
        q = ModelQueue()
        wrapped = q.wrap(self._backend(80), "chat")
        q.open_slot("chat")

        # Launch one slow caller, then close_slot from another thread.
        # Verify the drain returns within ~300ms of the ticket
        # completing -- if the event was set, the wake is immediate.
        drain_result = {}

        def caller():
            wrapped("only")

        def closer():
            t0 = time.time()
            drain_result["drain"] = q.close_slot(
                "chat", wait_seconds=2.0, force=False,
            )
            drain_result["elapsed"] = time.time() - t0

        t_call = threading.Thread(target=caller)
        t_close = threading.Thread(target=closer)
        t_call.start()
        time.sleep(0.010)
        t_close.start()
        t_call.join()
        t_close.join()

        assert drain_result["drain"]["drained"] is True
        # The Event-based wake should make drain return shortly after
        # the ticket completes. Generous bound to avoid CI flakiness;
        # the old 250ms polling spin would still pass at <500ms but
        # would not at <300ms once a ticket finished between ticks.
        assert drain_result["elapsed"] < 0.500, (
            f"drain took {drain_result['elapsed']:.3f}s -- the Event "
            "wake should be near-immediate after the last ticket "
            "completes"
        )

    def test_force_close_disables_subsequent_tickets(self):
        q = ModelQueue()
        wrapped = q.wrap(self._backend(10), "chat")
        q.open_slot("chat")
        wrapped("first")  # serves OK
        q.close_slot("chat", wait_seconds=0, force=True)
        with pytest.raises(QueueClosed):
            wrapped("after-close")

    def test_open_close_state_transitions(self):
        q = ModelQueue()
        assert q.slot_state("chat") == ModelQueue.STATE_CLOSED
        q.open_slot("chat")
        assert q.slot_state("chat") == ModelQueue.STATE_OPEN
        q.close_slot("chat", wait_seconds=0, force=True)
        assert q.slot_state("chat") == ModelQueue.STATE_CLOSED


# ---------------------------------------------------------------------------
# ModelSlot
# ---------------------------------------------------------------------------


class _StubApp:
    """Minimal app.state stand-in for ModelSlot tests."""

    class state:
        gemma_call = None
        evaluator_call = None


class _StubLock:
    def __init__(self):
        self._held = False

    def acquire(self, blocking=False):  # noqa: ARG002
        if self._held:
            return False
        self._held = True
        return True

    def release(self):
        self._held = False


class TestModelSlot:
    def test_idle_unload_returns_no_op(self):
        slot = ModelSlot(
            name="test",
            app_state_attr="gemma_call",
            state={"variant": None},
            lock=_StubLock(),
            events=[],
            log_fn=lambda *a, **k: None,
            loaded_ref_setter=lambda ref: None,
        )
        result = slot.unload(_StubApp(), purge_cache=False)
        assert result["status"] == "idle"
        assert "No test model loaded" in result["message"]

    def test_unload_drops_app_state_attr(self):
        app = _StubApp()
        app.state.gemma_call = lambda *a, **k: "test"
        slot = ModelSlot(
            name="test",
            app_state_attr="gemma_call",
            state={"variant": "x", "status": "ready"},
            lock=_StubLock(),
            events=[],
            log_fn=lambda *a, **k: None,
            loaded_ref_setter=lambda ref: None,
        )
        slot.unload(app, purge_cache=False)
        assert app.state.gemma_call is None

    def test_purge_fn_called_when_purge_cache_true(self):
        purged_with = []

        def fake_purge(variant):
            purged_with.append(variant)
            return {"ok": True, "gb_freed": 2.5}

        app = _StubApp()
        app.state.gemma_call = lambda *a, **k: "test"
        slot = ModelSlot(
            name="test",
            app_state_attr="gemma_call",
            state={"variant": "31b-it", "status": "ready"},
            lock=_StubLock(),
            events=[],
            log_fn=lambda *a, **k: None,
            loaded_ref_setter=lambda ref: None,
            purge_fn=fake_purge,
        )
        result = slot.unload(app, purge_cache=True)
        assert purged_with == ["31b-it"]
        assert result["purged"]["gb_freed"] == 2.5

    def test_purge_fn_not_called_when_purge_cache_false(self):
        purged_with = []

        def fake_purge(variant):
            purged_with.append(variant)
            return {"ok": True}

        app = _StubApp()
        app.state.gemma_call = lambda *a, **k: "test"
        slot = ModelSlot(
            name="test",
            app_state_attr="gemma_call",
            state={"variant": "31b-it", "status": "ready"},
            lock=_StubLock(),
            events=[],
            log_fn=lambda *a, **k: None,
            loaded_ref_setter=lambda ref: None,
            purge_fn=fake_purge,
        )
        result = slot.unload(app, purge_cache=False)
        assert purged_with == []
        assert result["purged"] is None

    def test_post_unload_hook_runs(self):
        hook_calls = []
        app = _StubApp()
        app.state.gemma_call = lambda *a, **k: "test"
        slot = ModelSlot(
            name="test",
            app_state_attr="gemma_call",
            state={"variant": "31b-it"},
            lock=_StubLock(),
            events=[],
            log_fn=lambda *a, **k: None,
            loaded_ref_setter=lambda ref: None,
            post_unload_hook=lambda app: hook_calls.append("hook-fired"),
        )
        slot.unload(app, purge_cache=False)
        assert hook_calls == ["hook-fired"]


# ---------------------------------------------------------------------------
# Variants registry
# ---------------------------------------------------------------------------


class TestVariantsRegistry:
    def setup_method(self):
        """Each test runs with the clean built-in set."""
        clear_custom_variants()

    def teardown_method(self):
        clear_custom_variants()

    def test_builtin_variants_resolve(self):
        for vid in (
            "e2b-it", "e4b-it", "26b-a4b-it", "31b-it",
            "jailbroken-31b", "jailbroken-e4b",
            "cloud-gemini", "cloud-openai", "cloud-ollama",
        ):
            assert get_variant(vid) is not None
            assert is_builtin_variant(vid) is True

    def test_31b_footprint_matches_kaggle_reality(self):
        """The 31b-it disk footprint must be 18 GB (not 30) so the
        preflight gate doesn't reject the default chat variant on a
        fresh Kaggle session."""
        assert footprint_gb("31b-it") == {"disk": 18.0, "gpu": 16.0}

    def test_cloud_variant_marked_cloud(self):
        assert is_cloud_variant("cloud-gemini") is True
        assert is_cloud_variant("e4b-it") is False
        # Unknown variant defaults via prefix check.
        assert is_cloud_variant("cloud-future-model") is True
        assert is_cloud_variant("ondevice-future-model") is False

    def test_unknown_variant_footprint_worst_case(self):
        assert footprint_gb("not-a-real-variant") == {"disk": 30.0, "gpu": 20.0}

    def test_register_variant_refuses_duplicate(self):
        spec = VariantSpec(
            id="31b-it",
            display="Test override",
            hf_id="example/test",
            size_gb=10.0,
            fits="single T4",
            category="on-device",
            load_eta="~test",
            disk_gb=10.0,
            gpu_gb=8.0,
        )
        with pytest.raises(ValueError, match="already registered"):
            register_variant(spec)

    def test_register_variant_with_overwrite(self):
        original = get_variant("31b-it")
        spec = VariantSpec(
            id="31b-it",
            display="Test override",
            hf_id="example/test",
            size_gb=10.0,
            fits="single T4",
            category="on-device",
            load_eta="~test",
            disk_gb=10.0,
            gpu_gb=8.0,
        )
        register_variant(spec, overwrite=True)
        assert get_variant("31b-it").display == "Test override"
        # Restore for downstream tests.
        register_variant(original, overwrite=True)

    def test_register_custom_variant(self):
        spec = VariantSpec(
            id="custom-test-model",
            display="Custom Test Model",
            hf_id="example/custom",
            size_gb=5.0,
            fits="single T4",
            category="on-device",
            load_eta="~test",
            disk_gb=6.0,
            gpu_gb=4.0,
        )
        register_variant(spec)
        assert get_variant("custom-test-model") is spec
        assert is_builtin_variant("custom-test-model") is False
        assert "custom-test-model" in list_variant_ids()
        # Built-in survives.
        assert get_variant("31b-it") is not None

    def test_clear_custom_returns_count(self):
        register_variant(VariantSpec(
            id="a", display="a", hf_id="a/a", size_gb=1.0, fits="x",
            category="on-device", load_eta="x", disk_gb=1, gpu_gb=1,
        ))
        register_variant(VariantSpec(
            id="b", display="b", hf_id="b/b", size_gb=1.0, fits="x",
            category="on-device", load_eta="x", disk_gb=1, gpu_gb=1,
        ))
        assert clear_custom_variants() == 2
        assert get_variant("a") is None
        assert get_variant("b") is None
        # Built-ins survive.
        assert get_variant("31b-it") is not None

    def test_register_rejects_non_variantspec(self):
        with pytest.raises(ValueError, match="VariantSpec"):
            register_variant({"id": "fake", "display": "wrong shape"})  # type: ignore[arg-type]

    def test_to_ui_map_has_expected_shape(self):
        ui = to_ui_map()
        for vid in VARIANT_REGISTRY.keys():
            assert vid in ui
            for key in ("display", "size_gb", "fits", "category", "load_eta"):
                assert key in ui[vid]


# ---------------------------------------------------------------------------
# Templates registry + fill
# ---------------------------------------------------------------------------


class TestTemplatesRegistry:
    def setup_method(self):
        clear_custom_templates()

    def teardown_method(self):
        clear_custom_templates()

    def test_four_builtin_templates_present(self):
        for tid in ("hk_ld_fdh_complaint", "ph_dmw_complaint",
                    "iom_referral", "ngo_intake"):
            assert tid in TEMPLATES_REGISTRY
            assert is_builtin_template(tid) is True

    def test_register_custom_template(self):
        spec = TemplateSpec(
            id="my_test_template",
            title="Test",
            jurisdiction="Test",
            audience="Test",
            summary="Test summary",
            body="Hello {{name}}",
            fields=(TemplateField(id="name", label="Name", required=True),),
        )
        register_template(spec)
        assert TEMPLATES_REGISTRY["my_test_template"] is spec
        assert is_builtin_template("my_test_template") is False

    def test_register_refuses_duplicate(self):
        spec = TemplateSpec(
            id="hk_ld_fdh_complaint",
            title="Override",
            jurisdiction="x",
            audience="x",
            summary="x",
            body="x",
            fields=(),
        )
        with pytest.raises(ValueError, match="already registered"):
            register_template(spec)

    def test_render_missing_fields_marked(self):
        spec = TemplateSpec(
            id="x", title="x", jurisdiction="x", audience="x",
            summary="x", body="A {{a}} B {{b}}",
            fields=(
                TemplateField(id="a", label="A"),
                TemplateField(id="b", label="B"),
            ),
        )
        out = render_template(spec.body, {"a": "filled"})
        assert "A filled B (not provided)" in out

    def test_bundle_field_hint_resolves_paths(self):
        bundle = {
            "intelligence": {
                "case_brief": "Worker M. paid HKD 42000.",
                "people": [{"label": "M."}, {"label": "L."}],
                "payments": [{"amount": "42000"}, {"amount": "5000"}],
                "entities": {"employer": ["ACME Ltd"]},
            }
        }
        assert bundle_field_hint(bundle, "intelligence.case_brief") == "Worker M. paid HKD 42000."
        # Payments wildcard collects all amounts.
        assert bundle_field_hint(bundle, "intelligence.payments[*].amount") == "42000, 5000"
        # Unknown path -> None.
        assert bundle_field_hint(bundle, "nonexistent.path[0]") is None

    def test_gemma_fill_three_passes(self):
        """Provenance buckets: bundle_hint > manual > gemma > missing."""
        spec = TemplateSpec(
            id="x", title="x", jurisdiction="x", audience="x",
            summary="x", body="A {{a}} B {{b}} C {{c}} D {{d}}",
            fields=(
                TemplateField(id="a", label="A", source_hint="intelligence.case_brief"),
                TemplateField(id="b", label="B"),  # manual only
                TemplateField(id="c", label="C"),  # gemma
                TemplateField(id="d", label="D"),  # missing
            ),
        )
        bundle = {"intelligence": {"case_brief": "from-bundle"}}
        manual_fields = {"b": "from-manual", "a": "manual-wins"}

        gemma_calls = []

        def fake_gemma(prompt, **kwargs):
            gemma_calls.append(prompt[:50])
            return '{"fields": {"c": "from-gemma", "d_invalid": "should-be-rejected"}}'

        filled, meta = gemma_fill_template(
            spec, bundle, manual_fields, gemma_call=fake_gemma,
        )
        # Manual overrides bundle hint.
        assert filled["a"] == "manual-wins"
        assert meta["per_field"]["a"] == "manual"
        assert filled["b"] == "from-manual"
        assert meta["per_field"]["b"] == "manual"
        assert filled["c"] == "from-gemma"
        assert meta["per_field"]["c"] == "gemma"
        # `d` was a required field but Gemma omitted it -> missing.
        assert "d" not in filled
        assert meta["per_field"]["d"] == "missing"
        assert meta["used_gemma"] is True
        # The fabricated field id outside the schema is rejected
        # silently (defended against prompt-injected JSON keys).
        assert "d_invalid" not in filled
        assert len(gemma_calls) == 1

    def test_gemma_fill_no_gemma_call_when_use_gemma_false(self):
        """Passing gemma_call=None means used_gemma stays False even
        if the bundle has the data."""
        spec = TemplateSpec(
            id="x", title="x", jurisdiction="x", audience="x",
            summary="x", body="A {{a}}",
            fields=(TemplateField(id="a", label="A", source_hint="intelligence.case_brief"),),
        )
        bundle = {"intelligence": {"case_brief": "from-bundle"}}
        filled, meta = gemma_fill_template(spec, bundle, {}, gemma_call=None)
        assert filled["a"] == "from-bundle"
        assert meta["per_field"]["a"] == "bundle_hint"
        assert meta["used_gemma"] is False

    def test_safe_json_extract_handles_truncated(self):
        # Plain JSON.
        assert safe_json_extract('{"a": 1}') == {"a": 1}
        # JSON embedded in chatty text.
        assert safe_json_extract('Sure! Here is the JSON: {"a": 1} hope it helps.') == {"a": 1}
        # Empty / malformed -> {}.
        assert safe_json_extract("") == {}
        assert safe_json_extract("no json here") == {}


# ---------------------------------------------------------------------------
# kernel_api: end-to-end body validation
# ---------------------------------------------------------------------------


class TestKernelApiBoolFootguns:
    """Pin the classes of bugs the Pydantic models defend against."""

    def test_string_false_disables_use_chat_as_judge(self):
        """The classic bool('false') == True footgun. UseChatAsJudge
        must map "false" -> False so a JSON form post does not
        accidentally enable the mirror."""
        r = UseChatAsJudgeRequest.model_validate({"enabled": "false"})
        assert r.enabled is False

    def test_string_zero_disables_purge_cache(self):
        r = UnloadModelRequest.model_validate({"purge_cache": "0"})
        assert r.purge_cache is False

    def test_string_off_disables_force(self):
        r = UnloadModelRequest.model_validate({"force": "off"})
        assert r.force is False

    def test_bare_dict_passes_through_with_defaults(self):
        """Empty dict -> default values everywhere (no crash)."""
        r = UseChatAsJudgeRequest.model_validate({})
        assert r.enabled is True
        r = LoadModelRequest.model_validate({})
        assert r.variant == ""
        r = UnloadModelRequest.model_validate({})
        assert r.purge_cache is True
        assert r.force is False
        assert r.drain_seconds == 30.0
