from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_docker_workflow_targets_master_and_manual_runs_are_build_only():
    workflow = (ROOT / ".github/workflows/docker-publish.yml").read_text(
        encoding="utf-8"
    )

    assert "branches: [master]" in workflow
    assert "branches: [main]" not in workflow
    assert 'default: false' in workflow
    assert "workflow_dispatch' && inputs.push" in workflow
    assert workflow.count("github.ref_type == 'tag'") == 4
    assert "github.event_name == 'push' ||" not in workflow
    assert "sigstore/cosign-installer@v4" in workflow
    assert "cosign sign --yes" in workflow
    assert "steps.build.outputs.digest" in workflow


def test_helm_workflow_has_nonpublishing_manual_preflight():
    workflow = (ROOT / ".github/workflows/helm-publish.yml").read_text(
        encoding="utf-8"
    )

    assert 'description: "Publish to the chart repository' in workflow
    assert "default: false" in workflow
    assert "helm lint infra/helm/duecare" in workflow
    assert "helm template duecare infra/helm/duecare" in workflow
    assert "helm package infra/helm/duecare" in workflow
    assert "actions/upload-artifact@v7" in workflow
    assert "inputs.publish" in workflow


def test_helm_and_container_defaults_use_the_same_gemma4_model():
    values = (ROOT / "infra/helm/duecare/values.yaml").read_text(encoding="utf-8")
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert values.count("gemma4:e2b") >= 4
    assert "gemma2:2b" not in values
    assert "ENV DUECARE_OLLAMA_MODEL=gemma4:e2b" in dockerfile
