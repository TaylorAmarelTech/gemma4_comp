<!-- audit-allow-file:drift
reason: this doc literally enumerates the drift terms the audit looks
for (OpenClaw, signed pack, 76-notebook, "Privacy is non-negotiable",
6 core + 5, etc.). Without this marker the audit recursively flags
its own documentation. The header-only marker placement (within the
first 12 lines) means body code blocks that show marker syntax can't
accidentally opt out of unrelated files.
-->

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
- **kaggle_lane_labels** — every `kaggle/{01,02,03,A-*}/README.md`
  carries a `<!-- duecare:lane-label -->` block or `Serves lanes:` line
  so a reviewer clicking from the website sees continuity

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

Add `audit-allow-file:drift` as an HTML comment within the first 12
lines of the file when an entire doc is intrinsically about the
deprecated term. Body examples and prose mentions are ignored, so docs
that explain this syntax do not accidentally opt out:

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

## Claude Code harness layer

Three third-party Claude Code plugins are installed at user scope on
the author's machine and complement the in-repo audit gate. They're
documented here so future contributors get the same setup.

### What's installed

| Plugin | Source | Adds | Trigger / use |
|---|---|---|---|
| **Hokage** (`claude-code-harness`) | `Chachamaru127/claude-code-harness` (MIT) | Plan→Work→Review→Ship loop · Go-native hook engine (~10ms PreToolUse / PostToolUse / PreCompact) · 4 agents (advisor, reviewer, scaffolder, worker) · 9 verb skills (`harness-plan`, `harness-work`, `harness-review`, `harness-release`, `harness-setup`, `harness-sync`, `harness-loop`, `harness-accept`, `harness-plan-brief`) · runtime safety policies | Activates automatically; verb skills available as slash commands. Per-project policies live in `harness.toml` at the repo root (SSOT). |
| **Harness** (`harness@harness-marketplace`) | `revfactory/harness` (Apache-2.0) | Meta-skill that scaffolds 3-5 specialized agents into `.claude/agents/` + supporting skills into `.claude/skills/` based on a one-sentence project description. 6 architectures (Pipeline, Fan-out/Fan-in, Expert Pool, Producer-Reviewer, Supervisor, Hierarchical Delegation). | Type *"build a harness for the duecare migrant-worker safety project"*. Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` (set in `.claude/settings.json`). |
| **ECC** (`everything-claude-code`) | `affaan-m/everything-claude-code` (MIT) | 48 agents · 68 commands · 182 skills · 89 rule files · 2 hooks. Notable: `/code-review`, `/build-fix`, `/plan`, `/checkpoint`, `/learn`, `/skill-create`, `/feature-dev`, `/quality-gate`, language-specific build/review/test (cpp/flutter/go/kotlin/python/rust). All ECC content is namespaced under `~/.claude/rules/ecc/` and `~/.claude/skills/ecc/`. | Slash commands available in any session. Re-apply via `cd /tmp/everything-claude-code && bash install.sh python` (needs `npm install` first). |

### Install for a fresh contributor

```bash
# All three plugins land at user scope (~/.claude/plugins/),
# do not modify the project's .claude/ directory.
claude plugin marketplace add Chachamaru127/claude-code-harness
claude plugin marketplace add revfactory/harness
claude plugin marketplace add affaan-m/everything-claude-code

claude plugin install claude-code-harness@claude-code-harness-marketplace
claude plugin install harness@harness-marketplace
claude plugin install everything-claude-code@everything-claude-code

# ECC also has an apply step that writes 452 namespaced files to
# ~/.claude/rules/ecc/ + ~/.claude/skills/ecc/ — opt-in:
git clone https://github.com/affaan-m/everything-claude-code.git /tmp/ecc
cd /tmp/ecc && npm install && node scripts/install-apply.js python
```

`claude plugin list` should then show all three with `Status: ✔ enabled`.

### Per-project policy (`harness.toml`)

Hokage reads `harness.toml` at the repo root for safety policies:

- `[safety.permissions].deny` — never (sudo, raw secrets, `_reference/`)
- `[safety.permissions].ask` — always confirm (recursive deletes,
  history-rewriting git, `pip install`, `kaggle kernels push`,
  `huggingface-cli upload`)
- `[safety.permissions].protectedBranchPush = "ask"` — confirm
  before direct push to `master` (Render auto-deploys, so
  Claude Code asks each time)
- `[safety.sandbox.network].deniedDomains` — block cloud-metadata
  exfil endpoints + paste sites
- `[safety.sandbox.filesystem].denyRead` — `_reference/`,
  `raw_python/`, `evidence_raw/`, `.env`, `.ssh/`, `.aws/`

**Source of truth.** Edit `harness.toml` then run `harness sync` to
regenerate `.claude-plugin/settings.json` (gitignored). Do NOT
hand-edit `.claude-plugin/settings.json` — Hokage's self-protection
denies it and `harness sync` will overwrite it.

### Project Claude Code config (`.claude/settings.json`)

Separate from the Hokage `.claude-plugin/settings.json` (which is
gitignored and machine-local). The `.claude/settings.json` is
committed and contains:

- `env` — `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` (so revfactory/harness
  meta-skill works) + `DUECARE_DATA_DIR=.duecare-smoke` (so the hub
  TestClient smoke runs use a sandbox)
- `permissions.allow` — exact-form allowlist for the audit + verify
  toolchain so Claude Code doesn't prompt on routine commands

### Recommended workflow

For a polish-pass session:

1. Start a fresh Claude Code session in this repo (Hokage hooks
   activate at session start).
2. Use the ECC `/plan` slash command to scope the change.
3. Make the edit. Hokage's PreToolUse hook will gate destructive
   commands per `harness.toml`.
4. Run `/audit` (our local slash command) to gate against the four
   public-surface drift categories.
5. Use ECC `/code-review` for a final pass.
6. Commit. The pre-push git hook runs the audit again.
7. CI's `validate-public-surface` job confirms on push.
