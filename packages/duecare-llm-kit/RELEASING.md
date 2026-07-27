# Releasing `duecare-llm-kit`

The kit is locally artifact-ready, but it is not published on PyPI. The same is
true for all 18 `duecare-llm*` workspace distributions (verified 2026-07-27).

## Local artifact evidence

The 2026-07-21 clean-environment receipt remains useful:

| Check | Result |
|---|---|
| `python -m build` | Wheel and source distribution built |
| `python -m twine check dist/*` | Both passed |
| clean-room wheel install | Installed with declared base dependencies |
| `import duecare.kit` | Version `0.1.0` imported |
| deterministic scan and verifier | 12 indicator keys and 5/5 verifier criteria |
| console entry points | `duecare-kit-report` and `duecare-kit-corpus` resolved |

This proves local package construction, not registry publication or the
18-package release as a whole.

## Current registry boundary

Direct `twine upload` is not an approved path. It would bypass the repository's
sole-publisher, OIDC, environment-approval, inventory, and version checks.

`.github/workflows/pypi-publish.yml` is the only publisher:

- manual runs build only by default and may target TestPyPI;
- manual runs cannot target production PyPI;
- generic repository `v*` tags do not publish packages; and
- production requires `packages-vMAJOR.MINOR.PATCH`, with all 18 package
  versions matching that tag.

The workspace intentionally fails a `packages-v0.1.0` preflight today:
`duecare-llm-chat` is `0.17.0`, `duecare-llm-server` is `0.1.2`, and the other
distributions are `0.1.0`.

## Owner-approved release sequence

1. Choose and document coordinated versions or replace the coordinated policy
   with a reviewed per-package release manifest/workflow. Cleanup work must not
   infer this decision.
2. Reconcile package versions, dependency ranges, changelog, release notes, and
   the currently unversioned `CITATION.cff`.
3. Run:

   ```bash
   python scripts/validate_package_release.py
   python scripts/validate_publication_readiness.py --scope core
   ```

4. Run the GitHub workflow in `build-only` mode. Download all 18 wheels and
   source distributions, verify hashes, and clean-install the intended set.
5. Use the workflow's TestPyPI option and verify installation from that
   registry. Do not use it as production evidence.
6. Confirm trusted-publisher and protected-environment settings for this exact
   repository/workflow, then create the reviewed package tag.
7. Confirm every intended name/version is visible and clean-installable before
   changing public docs to show bare `pip install` as a live path.

## After publication

- Update the package inventory, install guide, website, notebooks, changelog,
  citation metadata, and handoff together.
- Preserve the exact tag, artifact hashes, clean-install receipt, and PyPI URLs.
- Bump development versions deliberately; never overwrite an existing version.
- Keep `dist/` and `build/` ignored. Registry artifacts are release evidence,
  not source files to commit.

Optional extras remain `viz`, `nlp`, and `all`; their installability must be
tested against the published version before advertising those commands as live.
