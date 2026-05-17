from __future__ import annotations

from fastapi.testclient import TestClient

from duecare.chat.app import KO_BRANCHES, create_app
from duecare.chat.harnesses import all_harnesses
from duecare.chat.harnesses.base import (
    HarnessLogicPath,
    HarnessModelTarget,
    HarnessPackContract,
    HarnessSpec,
    MODEL_CAPABILITIES,
    MODEL_TRANSPORTS,
    contract_from_module,
)


STANDARD_FIELDS = {
    "logic_paths",
    "knowledge_packs",
    "logic_packs",
    "model_io",
    "model_targets",
    "input_verification",
    "output_verification",
    "privacy_boundaries",
}


def test_harness_spec_exposes_standardized_logic_pack_and_verification_fields():
    valid_ko = set(KO_BRANCHES)
    for module in all_harnesses():
        name = module.name
        spec = module.spec
        assert isinstance(spec, HarnessSpec), name
        assert spec.logic_paths, name
        assert spec.model_io, name
        assert spec.model_targets, name
        assert spec.input_verification, name
        assert spec.output_verification, name
        assert spec.privacy_boundaries, name

        for path in spec.logic_paths:
            assert isinstance(path, HarnessLogicPath), name
            assert path.id and path.label and path.steps, name
            assert path.model_call in {"none", "optional", "hybrid", "required", "external_optional"}, name
            assert set(path.consumes).issubset(valid_ko), (name, path.id, path.consumes)
            assert set(path.emits).issubset(valid_ko), (name, path.id, path.emits)

        for pack in (*spec.knowledge_packs, *spec.logic_packs):
            assert isinstance(pack, HarnessPackContract), name
            assert pack.id and pack.label, name
            assert pack.kind in {"knowledge_pack", "logic_pack"}, name
            assert set(pack.types).issubset(valid_ko), (name, pack.id, pack.types)

        default_targets = [target for target in spec.model_targets if target.default]
        assert default_targets, name
        for target in spec.model_targets:
            assert isinstance(target, HarnessModelTarget), name
            assert target.id and target.label and target.role, name
            assert target.transport in MODEL_TRANSPORTS, (name, target.transport)
            assert set(target.capabilities).issubset(set(MODEL_CAPABILITIES)), (
                name,
                target.id,
                target.capabilities,
            )


def test_contract_from_module_serializes_standard_fields():
    for module in all_harnesses():
        contract = contract_from_module(module)
        assert STANDARD_FIELDS.issubset(contract), module.name
        assert isinstance(contract["logic_paths"], list) and contract["logic_paths"], module.name
        assert isinstance(contract["knowledge_packs"], list), module.name
        assert isinstance(contract["logic_packs"], list), module.name
        assert isinstance(contract["model_io"], dict) and contract["model_io"], module.name
        assert isinstance(contract["model_targets"], list) and contract["model_targets"], module.name
        assert isinstance(contract["input_verification"], list), module.name
        assert isinstance(contract["output_verification"], list), module.name
        assert isinstance(contract["privacy_boundaries"], list), module.name
        for path in contract["logic_paths"]:
            assert {"id", "label", "steps", "model_call", "verification"}.issubset(path), module.name
        for target in contract["model_targets"]:
            assert {"id", "label", "transport", "role", "capabilities", "trust_boundary"}.issubset(target), module.name


def test_harnesses_endpoint_exposes_standard_fields_to_ui():
    client = TestClient(create_app())
    data = client.get("/api/harnesses").json()
    assert STANDARD_FIELDS.issubset(set(data["contract_fields"]))
    by_name = {item["name"]: item for item in data["harnesses"]}
    assert by_name["chat"]["logic_paths"][0]["id"] == "chat_response"
    assert by_name["search_safety"]["logic_paths"][0]["id"] == "sanitize_query"
    assert by_name["post_search_verification"]["logic_paths"][0]["id"] == "verify_search_results"
    assert by_name["post_search_verification"]["model_targets"][0]["trust_boundary"] == "local"
    assert by_name["import_corpus"]["model_io"]["model_transport"].startswith("none")
    assert by_name["chat"]["model_targets"][0]["transport"] == "gemma4_runtime"
    assert by_name["search"]["model_targets"][0]["transport"] == "none"
