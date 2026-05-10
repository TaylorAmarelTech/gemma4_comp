# Public-surface audit

`scripts/validate_public_surface.py` is a single command that gates
the public surface against drift we've seen real cases of:

- **drift_terms** — stale wording (`6 core + 5`, `76-notebook`,
  `OpenClaw` in active prose, `signed pack`, unverified CLI commands,
  `Privacy is non-negotiable.` as an h1–h3 headline)
- **hub_routes_200** — every `PAGE_ROUTES` entry plus every link in
  `_nav.html` and `_footer.html` returns 200 via FastAPI TestClient
- **five_lane_order** — the canonical lane order
  (Platform safety → NGO & regulator → Individual worker / mobile →
  Researcher → Developer / integration partner) appears on
  `setup.html` and `use-cases.html`
- **kaggle_lane_labels** — every `kaggle/{01,02,A-*}/README.md` carries
  a `<!-- duecare:lane-label -->` block or `Serves lanes:` line so a
  judge clicking from the website sees continuity

## Run it

```bash
.venv/Scripts/python.exe scripts/validate_public_surface.py
.venv/Scripts/python.exe scripts/validate_public_surface.py --json
.venv/Scripts/python.exe scripts/validate_public_surface.py --skip drift_terms
```

Slash-command equivalent inside Claude Code:

```
/audit
```

Exit 0 = green. Exit 1 = at least one finding.

## Allowlisting legitimate references

Drift terms sometimes appear in active surfaces on purpose:

- The writeup explains a rename (`Legacy OpenClaw aliases remain as
  redirects ...`)
- An env-var table documents the literal name a third-party API
  expects (e.g. `OPENCLAW_API_KEY` for the OpenClaw research tool
  integration — renaming it would break users)
- A package README documents an actual class name (`OpenClawTool`)

Two opt-out mechanisms:

### Per-line (or 1-line block)

Add `audit-allow:drift` to the matching line OR the line directly
above. Markdown comment example:

```markdown
<!-- audit-allow:drift  reason: documents the rename publicly -->
> Legacy OpenClaw aliases remain as redirects ...
```

Inside an env-var table row, append it as a trailing HTML comment:

```markdown
| `OPENCLAW_API_KEY` | (unset) | OpenClaw API key | <!-- audit-allow:drift literal env name -->
```

### Per-file

Add `audit-allow-file:drift` anywhere in the file (typically near the
top in a comment) when an entire doc is intrinsically about the
deprecated term:

```markdown
<!-- audit-allow-file:drift
reason: this README documents the OpenClawTool class which is real
code; class rename is queued separately.
-->
```

The check that is suppressed is **only `drift_terms`**. Route /
five-lane / kaggle-lane checks have no allowlist — they should always
run.

## Wire-up

Standalone: `scripts/validate_public_surface.py`.

Slash command: `.claude/commands/audit.md`.

CI: a non-blocking `validate-public-surface` job under
`.github/workflows/ci.yml` runs the script on every push and PR,
posts the report as a job summary, and is configured to warn (not
fail) until we eliminate the legitimate-but-unmarked findings.
Promote to blocking once the audit is consistently green.
