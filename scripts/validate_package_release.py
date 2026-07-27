#!/usr/bin/env python3
"""Validate the offline Python-package release surface.

This check never contacts PyPI. It reconciles the workspace inventory, the
canonical build order, the reviewed per-package release manifest, documented
versions, and GitHub Actions ownership. When a release tag is supplied, it
fails closed unless the tag selects exactly one manifest package at its current
version.
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
RELEASE_MANIFEST_PATH = ROOT / "configs" / "duecare" / "package_release.toml"
WORKFLOWS_DIR = ROOT / ".github" / "workflows"
PUBLISH_WORKFLOW = WORKFLOWS_DIR / "pypi-publish.yml"
RELEASE_TAG_RE = re.compile(
    r"^package-(?P<name>duecare-llm(?:-[a-z0-9]+)*)-v"
    r"(?P<version>[0-9]+\.[0-9]+\.[0-9]+)$"
)
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


def release_manifest() -> tuple[dict[str, object], list[Package]]:
    data = tomllib.loads(RELEASE_MANIFEST_PATH.read_text(encoding="utf-8"))
    entries = [
        Package(
            directory=str(entry["directory"]),
            name=str(entry["name"]),
            version=str(entry["version"]),
        )
        for entry in data.get("packages", [])
    ]
    return data, entries


def selected_directories(
    packages: list[Package], *, tag: str | None = None, package: str = "all"
) -> list[str]:
    """Resolve a reviewed manual selector or production tag to directories."""
    if tag:
        match = RELEASE_TAG_RE.fullmatch(tag)
        if not match:
            return []
        selected_name = match.group("name")
        return [item.directory for item in packages if item.name == selected_name]
    if package == "all":
        by_directory = {item.directory: item for item in packages}
        return [directory for directory in DEFAULT_BUILD_ORDER if directory in by_directory]
    return [
        item.directory
        for item in packages
        if package in {item.name, item.directory}
    ]


def validate(
    tag: str | None = None, package: str = "all"
) -> tuple[list[Package], list[Finding]]:
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

    try:
        manifest, manifest_packages = release_manifest()
    except (OSError, KeyError, TypeError, tomllib.TOMLDecodeError) as exc:
        manifest = {}
        manifest_packages = []
        findings.append(Finding("release manifest", f"cannot load manifest: {exc}"))
    if manifest:
        expected_headers = {
            "schema_version": "duecare.package-release.v1",
            "policy": "independent-semver",
            "production_tag_template": "package-{name}-v{version}",
        }
        for key, expected in expected_headers.items():
            if manifest.get(key) != expected:
                findings.append(
                    Finding(
                        "release manifest",
                        f"{key} must be {expected!r}, got {manifest.get(key)!r}",
                    )
                )
        manifest_directories = [item.directory for item in manifest_packages]
        if manifest_directories != DEFAULT_BUILD_ORDER:
            findings.append(
                Finding(
                    "release manifest",
                    "package rows must exactly match the canonical build order",
                )
            )
        actual_by_directory = {item.directory: item for item in packages}
        manifest_by_directory = {item.directory: item for item in manifest_packages}
        if manifest_by_directory != actual_by_directory:
            findings.append(
                Finding(
                    "release manifest",
                    "manifest names/versions differ from workspace pyprojects",
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
        "package-duecare-llm*-v*.*.*",
        "scripts/validate_package_release.py",
        "--print-directories",
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
                Finding(
                    "release tag",
                    "expected package-duecare-llm[-component]-vMAJOR.MINOR.PATCH, "
                    f"got {tag!r}",
                )
            )
        else:
            release_name = match.group("name")
            release_version = match.group("version")
            matches = [item for item in packages if item.name == release_name]
            if not matches:
                findings.append(
                    Finding(
                        "release tag", f"tag selects unknown package {release_name!r}"
                    )
                )
            elif matches[0].version != release_version:
                findings.append(
                    Finding(
                        "release tag version",
                        f"tag requests {release_name}={release_version}; "
                        f"workspace declares {matches[0].version}",
                    )
                )

    if package != "all" and not selected_directories(packages, package=package):
        findings.append(
            Finding("package selector", f"unknown package or directory {package!r}")
        )

    return packages, findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tag",
        help="optional package-duecare-llm[-component]-vMAJOR.MINOR.PATCH tag",
    )
    parser.add_argument(
        "--package",
        default="all",
        help="manual build selector: all, distribution name, or package directory",
    )
    parser.add_argument("--json", action="store_true", help="emit a machine-readable receipt")
    parser.add_argument(
        "--print-directories",
        action="store_true",
        help="print only the validated build directories for workflow composition",
    )
    args = parser.parse_args(argv)

    packages, findings = validate(args.tag, args.package)
    selection = selected_directories(packages, tag=args.tag, package=args.package)
    payload = {
        "package_count": len(packages),
        "packages": [asdict(package) for package in packages],
        "tag": args.tag,
        "package_selector": args.package,
        "selected_directories": selection,
        "findings": [asdict(finding) for finding in findings],
        "ready": not findings,
        "network_calls": 0,
        "model_calls": 0,
    }
    if args.print_directories:
        if not findings:
            print(" ".join(selection))
    elif args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"Package release surface: {len(packages)} packages, {len(findings)} findings")
        for finding in findings:
            print(f"[FAIL] {finding.check}: {finding.detail}")
        if not findings:
            print(
                "[PASS] inventory, per-package manifest, build order, "
                "documentation, and publication ownership agree"
            )
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
