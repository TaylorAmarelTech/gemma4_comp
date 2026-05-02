# Claude Code & Agentic Tooling Integration Plan

> Research findings + concrete integration recommendations for managing
> LLM context, hierarchies, and agentic workflows on this project. What's
> landscape, what's worth adopting, what we're already doing right.
>
> Last updated: 2026-04-11.
>
> **Path layout update (2026-04-18):** references to `src/forge/*` below
> describe the pre-package monolithic layout. Live code now lives under
> `packages/duecare-llm-*/src/duecare/*`. The hierarchical context
> precedence rule, `AGENTS.md` placement logic, and `.claude/rules/*.md`
> patterns described here are unchanged; only the file roots moved.

## TL;DR — what's landing in the project

| Adoption | Mechanism | Status | Effort |
|---|---|---|---|
| **AGENTS.md standard** (Linux Foundation) | 58 existing `AGENTS.md` files per-folder | ✅ already compliant | 0 |
| **Hierarchical `CLAUDE.md`** | Root + subtree, walks up the directory tree | ✅ already in place | 0 |
| **`.claude/rules/`** — auto-loaded rules | New directory, 5 rule files | 🟡 adding now | 30 min |
| **`.claude/commands/`** — project slash commands | `/forge-review`, `/forge-test`, `/forge-status`, `/review-architecture` | 🟡 adding now | 45 min |
| **GitHub Actions: `@claude` PR review** | `.github/workflows/claude.yml` (template) | 🟡 adding now, **user activates** | 15 min + 5 min user |
| **Repomix** for external LLM context exports | `repomix.config.json` + npm script | 🟡 adding now | 15 min |
| **GitHub MCP server** (official) | `.mcp.json` entry | 🟢 ready-to-install, optional | 10 min |
| **Claude Context MCP** (semantic search) | `.mcp.json` entry | 🟢 ready-to-install, optional | 10 min |
| **Spec-kit pattern** | GitHub's own AGENTS.md workflow | 🔵 reference only | — |
| **DueCare-native slash commands** | Project-local slash commands backed by the `duecare` CLI | 🟡 adding now | 30 min |

**Already compliant with three emerging standards without realizing it:**
the folder-per-module AGENTS.md structure I built matches the LF-stewarded
AGENTS.md standard; the CLAUDE.md hierarchy at project + subtree matches
Claude Code's auto-discovery; and the `duecare` CLI pattern is the same
pattern that powers `qdhenry/Claude-Command-Suite` and similar ecosystem
tools. The remaining work is mostly wiring, not design.

---

## 1. The AGENTS.md standard — research findings

### 1.1 Who stewards it

**AGENTS.md is now an open standard stewarded by the Agentic AI Foundation
under the Linux Foundation.** It was collaboratively developed across the
AI coding agent ecosystem (OpenAI Codex, Amp, Google Jules, Cursor,
Factory) and is now a formal spec at [agents.md](https://agents.md/).

### 1.2 Who supports it (as of 2026)

Native readers: **Claude Code, Cursor, GitHub Copilot, Gemini CLI,
Windsurf, Aider, Zed, Warp, RooCode, Codex CLI, Amp, Devin, Factory**,
and a growing list of others. If a coding agent reads markdown config,
it probably reads AGENTS.md.

### 1.3 The spec in two lines

1. **AGENTS.md is standard markdown.** No YAML frontmatter, no schema,
   no special sections required.
2. **The closest AGENTS.md to the file being edited wins.** Agents walk
   up from the file's folder, and the nearest AGENTS.md takes precedence
   on any conflicting instruction.

### 1.4 What this means for us — we're already compliant

Our folder-per-module scaffold (historical: `scripts/generate_forge.py`,
now archived under `_archive/scripts_one_off_2026-04/`) produced an
`AGENTS.md` file in every single module folder. Every one of those files
already has a "Do NOT" section, a "How to modify this module safely"
section, and explicit references to the surrounding meta files. When an
AI coding agent enters `src/forge/agents/judge/`, it reads that folder's
AGENTS.md first, which wins over anything higher up the tree.

**Zero migration cost.** We're doing it right already.

### 1.5 Small refinement to apply

The only thing the spec adds that we should explicitly document is the
**precedence rule**. I'm adding a note in the root `src/forge/AGENTS.md`
and the project `CLAUDE.md` that says "closest AGENTS.md wins" so future
readers (human or AI) don't assume the root AGENTS.md overrides
subfolders. That's a 10-second edit, not a rewrite.

---

## 2. Claude Code's CLAUDE.md hierarchy — research findings

### 2.1 Auto-discovery rules

Claude Code's memory system reads CLAUDE.md files in two ways:

1. **Walk-up on launch.** From the current working directory, Claude
   walks up to the repository root and concatenates every CLAUDE.md and
   CLAUDE.local.md it finds. All files join the context, in order.
2. **On-demand subtree loading.** CLAUDE.md files in subdirectories
   *below* the current working directory are loaded lazily — only when
   Claude actually accesses files in those subdirectories. This keeps
   active context focused and avoids wasting tokens on irrelevant parts
   of the tree.

### 2.2 File naming conventions

- `CLAUDE.md` — versioned, committed, shared with the team
- `CLAUDE.local.md` — gitignored, personal / experimental / secret-bearing
- `.claude/rules/*.md` — **auto-loaded at the project memory level for
  every `.md` file in the tree** (including subdirectories)

### 2.3 Import syntax

Memory files support `@path/to/file` imports. The referenced file is
inserted into context as a separate entry before the importing file. Use
this to compose CLAUDE.md from smaller, single-topic files when a single
monolithic CLAUDE.md grows past ~200 lines.

### 2.4 What this means for us — add `.claude/rules/`

Our current setup has:
- `CLAUDE.md` at the project root
- 58 folder-level `AGENTS.md` files (standard-compliant, as above)
- Memory files at `~/.claude/projects/.../memory/`

What's missing: the **`.claude/rules/`** auto-load directory. This is the
cleanest way to attach project-wide, always-active rules (never commit
PII, use Python 3.11+, run `duecare test` before pushing, etc.) without
bloating the root CLAUDE.md.

Adding now — see §8 for the rule files.

---

## 3. GitHub Actions integration — research findings

### 3.1 The official action

**`anthropics/claude-code-action@v1`** is in the GitHub Marketplace. It's
a general-purpose Claude Code action that:

- Detects `@claude` mentions in PR comments, issue comments, issue bodies
- Handles issue assignment automation
- Runs explicit automation tasks on dispatch
- Supports PR code review, path-specific reviews, external contributor
  reviews
- Authenticates via Anthropic direct API, Amazon Bedrock, Google Vertex
  AI, or Microsoft Foundry

### 3.2 The related actions

- **`anthropics/claude-code-base-action`** — lower-level building block
  for custom workflows (mirrors the base action's internals)
- **`anthropics/claude-code-security-review`** — specialized security-
  review action that analyzes code changes for vulnerabilities

### 3.3 Trigger model

Minimal workflow file triggers on `issue_comment`,
`pull_request_review_comment`, `issues`, and `pull_request_review`
events. Claude activates only when `@claude` is mentioned, so it doesn't
fire on every PR touch.

### 3.4 What this means for us — add a template workflow

We ship a `.github/workflows/claude.yml` as a template. The user adds
one GitHub repository secret (`ANTHROPIC_API_KEY`) and the workflow
activates. Once active, Claude becomes a project-aware PR reviewer that
reads our `CLAUDE.md`, our `AGENTS.md` files, and our `.claude/rules/`
on every review — so PR comments are grounded in the actual project
conventions, not generic "here's a best practice" boilerplate.

Adding now — see §9 for the workflow file.

---

## 4. MCP servers — research findings

### 4.1 What MCP is and why it matters here

**Model Context Protocol (MCP)** is an open standard for AI-tool
integration. MCP servers expose tools, resources, and prompts to a
Claude Code client via a well-defined schema. Claude Code's **Tool
Search** feature only pulls tool schemas on-demand — reducing context
usage by roughly 95% vs dumping every tool up-front — which means
adding an MCP server is nearly free in context cost.

### 4.2 Relevant MCP servers for this project

| Server | Maintainer | What it gives us |
|---|---|---|
| **`github/github-mcp-server`** | GitHub (official) | Query PRs / issues / releases / runs directly. Replaces ad-hoc `gh` calls. |
| **`zilliztech/claude-context`** | zilliztech | **Semantic code search** over the whole repository. Worth its weight in gold on a 638-file scaffold. |
| **`yamadashy/repomix`** (MCP variant) | yamadashy | Pack-on-demand: "show me the full context of the `duecare.agents` subtree" as one compiled file. |
| **`steipete/claude-code-mcp`** | steipete | Run Claude Code as an MCP server (agent-in-an-agent). Stretch goal for the Coordinator agent's actual implementation. |

### 4.3 What this means for us — ship a `.mcp.json` skeleton

I'm adding a `.mcp.json` at the project root with commented-out entries
for the four MCP servers above. The user can uncomment the ones they
want to activate. **Highest ROI for us: Claude Context** (semantic
search over 638 files is the killer feature for this scaffold).

---

## 5. Repository context compilers — research findings

### 5.1 The ecosystem

**Repomix** ([`yamadashy/repomix`](https://github.com/yamadashy/repomix))
is the strongest option. It:

- Packs the entire repo into a single AI-friendly file
- **Counts tokens** per file and for the whole repo (crucial for context-
  window planning)
- **Security-focused**: runs Secretlint on every file to prevent
  accidental inclusion of API keys, `.env` contents, etc.
- **Code compression** via tree-sitter: extracts key code elements
  (function signatures, class definitions) while dropping bodies, cutting
  tokens by 60-80% without losing structure
- Has an **MCP server variant** for Claude Code

**Alternatives** (not adopting, but good to know):
- **GitIngest** — zero-install, replace `hub` with `ingest` in any
  GitHub URL. Good for external one-off sharing, less good for
  day-to-day.
- **Code2prompt** — TUI-driven, Handlebars templating, glob filtering.
  Good for custom formats.

### 5.2 Why we want it

With 638 files in the DueCare scaffold plus `_reference/framework/` (another
~750 files) plus `_reference/trafficking_llm_benchmark/` (another
hundreds), we have two concrete needs:

1. **External LLM review** — if we want a second-opinion pass from
   GPT-4o-mini or Claude Haiku outside of Claude Code, Repomix gives us
   one file we can paste in.
2. **Context snapshots for debugging** — "what did the `duecare.agents`
   subtree look like at this git sha?" is a Repomix one-liner.

### 5.3 What this means for us — add a `repomix.config.json`

Ships with pre-configured includes/excludes. `_reference/`, `data/`,
`models/`, `__pycache__`, `.git/`, and `.venv*/` are excluded. The
`duecare` CLI gains a `forge compile-context` subcommand that calls
repomix with our config.

---

## 6. Slash commands and skills ecosystem — research findings

### 6.1 What's out there

- **`qdhenry/Claude-Command-Suite`** — 216+ slash commands, 12 skills,
  54 agents. The biggest community collection.
- **`wshobson/commands`** — production-ready commands
- **`hesreallyhim/awesome-claude-code`** — curated list (skills, hooks,
  slash commands, agents, plugins)
- **`alirezarezvani/claude-code-skill-factory`** — a toolkit for
  generating skills + slash commands programmatically
- **`aj-geddes/claude-code-bmad-skills`** — the BMAD (Business / Mission
  / Agent / Development) method as a skill bundle

### 6.2 Anatomy of a project-local slash command

Slash commands live in `.claude/commands/<name>.md`. The file is markdown
with instructions. When the user types `/<name>`, Claude executes the
file as a command prompt.

Skills live in `.claude/skills/<name>/SKILL.md`, one folder per skill,
with YAML frontmatter declaring when Claude should use the skill and
what tools it has access to.

### 6.3 What this means for us — build DueCare-native slash commands

Our `duecare` CLI (`duecare review`, `duecare test`, `duecare tree`, `forge
status`) is already well-suited to slash command wrappers. I'm adding:

- `/forge-review` — runs `duecare review` on a path, returns the meta-file
  contents
- `/forge-test` — runs `duecare test` on a path, returns pass/fail
- `/forge-status` — runs `duecare status`, returns completion report
- `/review-architecture` — loads `docs/architecture.md` +
  `docs/project_phases.md` and asks Claude to review consistency
- `/rubric-check` — loads `docs/rubric_alignment.md` and validates the
  current writeup draft against it

Each is a ~20-line markdown file. Low cost, high frequency-of-use value.

### 6.4 Skills we are **not** building yet

- `/new-module` — scaffolds a new DueCare module folder (future, when the
  DueCare CLI has a `forge new-module` subcommand)
- `/publish-submission` — orchestrates the full week-5 publication flow
  (future, after the publication layer is implemented)

These are good stretch goals for week 4 or 5.

---

## 7. Our hierarchy at a glance (after the additions in this doc)

```
gemma4_comp/
├── CLAUDE.md                     # project root (walks up)
├── AGENTS.md                     # project root (AGENTS.md standard)
├── .claude/
│   ├── rules/                    # auto-loaded at project level
│   │   ├── 00_safety_gate.md          # never commit PII, run anon gate
│   │   ├── 10_code_style.md           # Python 3.11+, Pydantic v2, type hints
│   │   ├── 20_test_before_commit.md   # duecare test before PR
│   │   ├── 30_forge_module_contract.md # folder-per-module pattern
│   │   └── 40_rubric_alignment.md     # video-first, 3-min, AGENTS.md, multimodal
│   └── commands/                 # project-local slash commands
│       ├── forge-review.md
│       ├── forge-test.md
│       ├── forge-status.md
│       ├── review-architecture.md
│       └── rubric-check.md
├── .github/
│   └── workflows/
│       └── claude.yml            # @claude PR review action (template)
├── .mcp.json                     # optional MCP servers (skeleton)
├── repomix.config.json           # repo context compiler config
│
├── src/forge/
│   ├── AGENTS.md                 # top-level (standard-compliant, closest-wins)
│   ├── CLAUDE.md                 # DueCare-specific conventions (NEW, small)
│   ├── core/
│   │   ├── AGENTS.md             # core-specific, wins over src/forge/AGENTS.md
│   │   └── contracts/
│   │       └── AGENTS.md         # contracts-specific, wins over core/AGENTS.md
│   ├── agents/
│   │   ├── AGENTS.md
│   │   └── judge/
│   │       └── AGENTS.md         # judge-specific, wins over all above
│   └── ...
│
└── docs/
    ├── architecture.md           # component architecture
    ├── project_phases.md         # 4-phase plan
    ├── integration_plan.md       # mapping existing assets -> DueCare
    ├── rubric_alignment.md       # honest scorecard + gap closers
    ├── kaggle_integration.md     # Kaggle CLI + compute
    └── claude_code_integration.md # this file
```

Context precedence, from weakest (loaded first) to strongest (wins
last):

```
~/.claude/CLAUDE.md                    # user-global
./CLAUDE.md                            # project root
./.claude/rules/*.md                   # auto-loaded rules
./src/forge/CLAUDE.md                  # DueCare-specific
./src/forge/AGENTS.md                  # DueCare-root AGENTS.md
./src/forge/agents/AGENTS.md           # agents-layer AGENTS.md
./src/forge/agents/judge/AGENTS.md     # judge-module AGENTS.md    <-- wins for edits in this folder
(explicit user instruction in chat)    # always wins over everything
```

This is the correct hierarchy per both Claude Code's memory rules and
the AGENTS.md standard's "closest-wins" precedence. We get it for free
because we're putting the right files in the right places.

---

## 8. What I'm adding now — `.claude/rules/`

Five auto-loaded rule files, short and specific. Each is <50 lines so
it costs minimal tokens but is always available.

See the files written alongside this doc in `.claude/rules/`.

---

## 9. What I'm adding now — `.github/workflows/claude.yml`

Template workflow for `@claude` PR review. **User activates by adding an
`ANTHROPIC_API_KEY` secret to the GitHub repo.** Until then it sits
inert — no extra cost, no extra risk.

See `.github/workflows/claude.yml`.

---

## 10. What I'm adding now — `.mcp.json` skeleton

Commented-out entries for:
- GitHub's official MCP server
- `zilliztech/claude-context` for semantic search
- Repomix MCP variant

User uncomments the ones they want active. Zero cost until activated.

See `.mcp.json`.

---

## 11. What I'm adding now — `repomix.config.json`

Pre-configured to exclude `_reference/`, `data/`, `models/`, `logs/`,
`__pycache__/`, `.venv*/`, and secrets. Token count reporting on, code
compression on. Output to `.repomix/forge-repo.txt` (gitignored).

Usage: `npx repomix` at the repo root (or `npm run compile-context` once
we add a `package.json` for it — but we don't have to if we're happy
with `npx`).

---

## 12. What I'm adding now — `.claude/commands/`

Five project-local slash commands, each ~20 lines:

- `/forge-review` — inspect a module folder
- `/forge-test` — run tests for a path
- `/forge-status` — whole-project completeness report
- `/review-architecture` — consistency check across architecture docs
- `/rubric-check` — check writeup against rubric alignment doc

These are invoked from Claude Code directly. They read our actual
project state (meta files + CLI output) and produce grounded responses.

---

## 13. What I'm NOT adding (and why)

Things I evaluated and decided against for now:

1. **BMAD method skill bundle** (`claude-code-bmad-skills`) — good
   structure but our project already has a clear architecture (DueCare)
   and we don't need a second organizing principle competing with it.
2. **The full 216-command Claude-Command-Suite** — useful reference but
   most of its commands are generic (code review, security audit,
   architectural analysis) and we have DueCare-specific needs. We cherry-
   pick ideas, we don't install the full bundle.
3. **`claude-code-security-review`** GitHub Action — duplicates what
   our own Validator agent will do on the trained model. Save for
   post-hackathon if we want CI-side security scans of the codebase
   itself.
4. **`spec-kit`** (GitHub's AGENTS.md spec workflow) — interesting but
   orthogonal to our workflow; we already have a clear specification
   flow via `docs/`.
5. **Running Claude Code as an MCP server via `steipete/claude-code-mcp`** —
   the Coordinator agent in DueCare is our own "agent-in-an-agent" pattern.
   Adding a second one creates confusion.
6. **A `package.json` for repomix** — unnecessary complexity. `npx
   repomix` works fine.

---

## 14. Activation checklist

After these files are in place, here's what the user needs to do to
activate each optional feature:

| Feature | User action | Blocking? |
|---|---|---|
| `.claude/rules/` auto-load | (none — Claude Code picks them up automatically) | no |
| `.claude/commands/` slash commands | (none — typed in the CLI) | no |
| Repomix compile-context | `npx repomix` on demand, or install globally | no |
| GitHub Actions `@claude` PR review | Add `ANTHROPIC_API_KEY` as a GitHub repo secret | yes-to-activate |
| GitHub MCP server | `claude mcp add github ...` per GitHub's install guide + GH token | yes-to-activate |
| Claude Context MCP (semantic search) | `claude mcp add claude-context ...` + first-index run | yes-to-activate |
| Repomix MCP variant | `claude mcp add repomix ...` | yes-to-activate |

Nothing ships pre-activated. The user chooses which optional features
to turn on. Zero risk of surprise network calls or API spend.

---

## 15. Sources

- [AGENTS.md — official standard](https://agents.md/)
- [AGENTS.md under the Agentic AI Foundation / Linux Foundation — announcement](https://vibecoding.app/blog/agents-md-guide)
- [GitHub spec-kit AGENTS.md](https://github.com/github/spec-kit/blob/main/AGENTS.md)
- [Claude Code memory docs](https://code.claude.com/docs/en/memory)
- [Claude Code project memory — nested directories (DEV Community)](https://dev.to/subprime2010/claude-code-project-memory-how-claudemd-files-work-across-nested-directories-1mk8)
- [How to Write a Good CLAUDE.md File — Builder.io](https://www.builder.io/blog/claude-md-guide)
- [anthropics/claude-code-action — GitHub](https://github.com/anthropics/claude-code-action)
- [Claude Code GitHub Actions docs](https://code.claude.com/docs/en/github-actions)
- [anthropics/claude-code-security-review](https://github.com/anthropics/claude-code-security-review)
- [GitHub MCP Server (official)](https://github.com/github/github-mcp-server)
- [Claude Context MCP (semantic search)](https://github.com/zilliztech/claude-context)
- [Repomix — GitHub](https://github.com/yamadashy/repomix)
- [Repomix docs](https://repomix.com/)
- [code2prompt — GitHub](https://github.com/mufeedvh/code2prompt)
- [Claude Command Suite — qdhenry](https://github.com/qdhenry/Claude-Command-Suite)
- [awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code)
- [Claude Code skills docs](https://code.claude.com/docs/en/skills)
- [Connect Claude Code to tools via MCP](https://code.claude.com/docs/en/mcp)
