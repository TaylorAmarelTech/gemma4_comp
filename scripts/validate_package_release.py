#!/usr/bin/env python3
"""Validate the offline Python-package release surface.

This check never contacts PyPI. It reconciles the workspace inventory, the
canonical build order, the documented versions, and GitHub Actions ownership.
When a release tag is supplied, it also fails closed unless every workspace
package has the coordinated version named by that tag.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path

# Executed as a sibling script, so ``scripts/`` is on sys.path at runtime.
from build_all_wheels import DEFAULT_BUILD_ORDER  # type: ignore[import-not-found]

ROOT = Path(__file__).resolve().parents[1]
PACKAGES_DIR = ROOT / "packages"
INVENTORY_PATH = ROOT / "docs" / "PACKAGE_INVENTORY.md"
WORKFLOWS_DIR = ROOT / ".github" / "workflows"
PUBLISH_WORKFLOW = WORKFLOWS_DIR / "pypi-publish.yml"
RELEASE_TAG_RE = re.compile(r"^packages-v(?P<version>[0-9]+\.[0-9]+\.[0-9]+)$")
INVENTORY_ROW_RE = re.compile(r"^\| `(?P<name>duecare-llm[^`]*)` \| (?P<version>[^ |]+) \|")
PUBLIC_INSTALL_TRUTH = {
    ROOT / "README.md": "No DueCare distribution is on PyPI yet",
    ROOT / "docs" / "deployment_local.md": "No DueCare distribution is on PyPI yet",
    ROOT / "docs" / "embedding_guide.md": "No DueCare distribution is on PyPI yet",
    ROOT / "docs" / "PACKAGE_INVENTORY.md": (
        "None of the 18 distributions is currently published on PyPI"
    ),
}


@dataclass(frozen=True)
class Package:
    directory: str
    name: str
    version: str


@dataclass(frozen=True)
class Finding:
    check: str
    detail: str


def workspace_packages() -> list[Package]:
    packages: list[Package] = []
    for path in sorted(PACKAGES_DIR.glob("duecare-llm*")):
        pyproject = path / "pyproject.toml"
        if not path.is_dir() or not pyproject.is_file():
            continue
        project = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]
        packages.append(Package(path.name, str(project["name"]), str(project["version"])))
    return packages


def documented_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for line in INVENTORY_PATH.read_text(encoding="utf-8").splitlines():
        match = INVENTORY_ROW_RE.match(line)
        if match:
            versions[match.group("name")] = match.group("version")
    return versions


def validate(tag: str | None = None) -> tuple[list[Package], list[Finding]]:
    packages = workspace_packages()
    findings: list[Finding] = []
    directories = [package.directory for package in packages]
    names = [package.name for package in packages]

    if len(packages) != 18:
        findings.append(
            Finding("workspace inventory", f"expected 18 packages, found {len(packages)}")
        )
    if len(names) != len(set(names)):
        findings.append(Finding("workspace inventory", "distribution names are not unique"))
    if set(directories) != set(DEFAULT_BUILD_ORDER):
        missing = sorted(set(directories) - set(DEFAULT_BUILD_ORDER))
        stale = sorted(set(DEFAULT_BUILD_ORDER) - set(directories))
        findings.append(
            Finding(
                "build order", f"workspace/build-order mismatch; missing={missing}, stale={stale}"
            )
        )

    documented = documented_versions()
    actual = {package.name: package.version for package in packages}
    if documented != actual:
        findings.append(
            Finding(
                "package inventory document",
                f"documented versions differ; documented={documented}, actual={actual}",
            )
        )

    publishers: list[str] = []
    for workflow in sorted(WORKFLOWS_DIR.glob("*.yml")):
        text = workflow.read_text(encoding="utf-8")
        if "pypa/gh-action-pypi-publish" in text or "twine upload" in text:
            publishers.append(workflow.name)
    if publishers != [PUBLISH_WORKFLOW.name]:
        findings.append(
            Finding(
                "publication ownership",
                f"expected only {PUBLISH_WORKFLOW.name}; found {publishers}",
            )
        )

    publish_text = PUBLISH_WORKFLOW.read_text(encoding="utf-8")
    required_markers = (
        "packages-v*.*.*",
        "scripts/validate_package_release.py",
        "pypa/gh-action-pypi-publish@release/v1",
        "DEFAULT_BUILD_ORDER",
    )
    for marker in required_markers:
        if marker not in publish_text:
            findings.append(Finding("publisher contract", f"missing marker: {marker}"))
    if "target == 'pypi'" in publish_text or 'target == "pypi"' in publish_text:
        findings.append(
            Finding("publisher contract", "manual production-PyPI target must stay disabled")
        )
    if re.search(r"^[ \t-]*[\"']?v\*", publish_text, re.MULTILINE):
        findings.append(Finding("publisher contract", "generic v* tag trigger is not allowed"))

    inventory_text = INVENTORY_PATH.read_text(encoding="utf-8")
    if "None of the 18 distributions is currently published on PyPI" not in inventory_text:
        findings.append(
            Finding("install truth", "canonical inventory lacks the unpublished-PyPI statement")
        )
    if "uv sync --all-packages" not in inventory_text:
        findings.append(
            Finding(
                "install truth", "canonical inventory lacks the workspace source-install command"
            )
        )
    for path, marker in PUBLIC_INSTALL_TRUTH.items():
        if marker not in path.read_text(encoding="utf-8"):
            findings.append(
                Finding(
                    "install truth",
                    f"{path.relative_to(ROOT).as_posix()} lacks marker: {marker}",
                )
            )

    for installer in (ROOT / "scripts" / "install.sh", ROOT / "scripts" / "install.ps1"):
        installer_text = installer.read_text(encoding="utf-8")
        missing_packages = [name for name in DEFAULT_BUILD_ORDER if name not in installer_text]
        if missing_packages:
            findings.append(
                Finding(
                    "source installer",
                    f"{installer.name} omits workspace packages: {missing_packages}",
                )
            )
        if "PyPI install failed" in installer_text or "--upgrade duecare-llm" in installer_text:
            findings.append(
                Finding(
                    "source installer", f"{installer.name} still probes unpublished PyPI projects"
                )
            )

    if tag:
        match = RELEASE_TAG_RE.fullmatch(tag)
        if not match:
            findings.append(
                Finding("release tag", f"expected packages-vMAJOR.MINOR.PATCH, got {tag!r}")
            )
        else:
            release_version = match.group("version")
            mismatches = [
                f"{package.name}={package.version}"
                for package in packages
                if package.version != release_version
            ]
            if mismatches:
                findings.append(
                    Finding(
                        "coordinated version",
                        f"tag requests {release_version}; mismatches: {', '.join(mismatches)}",
                    )
                )

    return packages, findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", help="optional packages-vMAJOR.MINOR.PATCH release tag")
    parser.add_argument("--json", action="store_true", help="emit a machine-readable receipt")
    args = parser.parse_args(argv)

    packages, findings = validate(args.tag)
    payload = {
        "package_count": len(packages),
        "packages": [asdict(package) for package in packages],
        "tag": args.tag,
        "findings": [asdict(finding) for finding in findings],
        "ready": not findings,
        "network_calls": 0,
        "model_calls": 0,
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"Package release surface: {len(packages)} packages, {len(findings)} findings")
        for finding in findings:
            print(f"[FAIL] {finding.check}: {finding.detail}")
        if not findings:
            print("[PASS] inventory, build order, documentation, and publication ownership agree")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
