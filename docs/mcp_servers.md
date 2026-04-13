# MCP server configuration for this project

> How to activate optional Model Context Protocol (MCP) servers that
> extend Claude Code with repo-aware tools. Schema-valid examples live
> in `.mcp.json.example` at the project root.

The active MCP config is `.mcp.json`. It ships **empty** (`mcpServers: {}`)
so there are no schema violations and nothing starts automatically. To
turn on an MCP server, copy the relevant block from `.mcp.json.example`
into `.mcp.json` and restart Claude Code.

## Why empty by default

Claude Code validates `.mcp.json` against the MCP schema at startup. Any
extra fields (including `_comment` keys or top-level notes objects) are
rejected and the whole file fails to parse. We keep documentation in
this markdown file and configuration examples in `.mcp.json.example`
rather than polluting the live config with fields the schema doesn't
allow.

Claude Code's Tool Search also loads MCP tool schemas on demand, so
there's no benefit to listing a server you don't actually use — it
doesn't speed up activation later.

## Available servers

### 1. GitHub MCP server (official)

**What it gives you:** query PRs, issues, releases, and workflow runs
for the project repo directly from Claude Code, without having to shell
out to `gh`.

**Source:** <https://github.com/github/github-mcp-server>

**Activation:**

1. Create a GitHub Personal Access Token with `repo`, `read:issues`,
   and `read:pull-request` scopes.
2. Store it as an environment variable:
   ```bash
   # Windows PowerShell
   setx GITHUB_PERSONAL_ACCESS_TOKEN "ghp_..."
   # macOS/Linux
   export GITHUB_PERSONAL_ACCESS_TOKEN="ghp_..."
   ```
3. Copy the `github` block from `.mcp.json.example` into `.mcp.json`.
4. Restart Claude Code.

**Requires:** Docker installed and running (the server is distributed
as a container from `ghcr.io/github/github-mcp-server`).

### 2. Claude Context (semantic code search)

**What it gives you:** embedding-based semantic search over the whole
repository. Ask questions like "where does the supervisor track retry
state?" and the MCP server returns the right file and lines without
walking the tree.

**Source:** <https://github.com/zilliztech/claude-context>

**Strongest fit for this project** — a 640-file folder-per-module tree
benefits enormously from semantic lookup over glob/grep.

**Activation:**

1. Choose an embedding provider and get an API key. OpenAI
   (`text-embedding-3-small`) is the default.
2. Set the key in your shell environment:
   ```bash
   export EMBEDDING_API_KEY="sk-..."
   ```
3. Copy the `claude-context` block from `.mcp.json.example` into
   `.mcp.json`.
4. Restart Claude Code. The first run indexes the repo; subsequent
   runs are fast.

**Requires:** Node.js 18+ (for `npx`).

### 3. Repomix MCP

**What it gives you:** on-demand packing of any subtree into a single
token-counted context blob. Useful for "give me the full context of
`duecare-llm-agents`" without juggling many Read calls.

**Source:** <https://github.com/yamadashy/repomix>

**Activation:**

1. Copy the `repomix` block from `.mcp.json.example` into `.mcp.json`.
2. Restart Claude Code.

**Requires:** Node.js 18+ (for `npx`).

## Secrets handling

- **Never commit real API keys** into `.mcp.json` or `.mcp.json.example`.
- Use shell environment variables and reference them by name in the
  `env` block (Claude Code expands them at launch).
- For per-session secrets, use `claude mcp env set <server> <KEY> <value>`
  which stores them in Claude Code's encrypted secret store.

## Validation

Claude Code's `/doctor` command validates `.mcp.json` against the MCP
schema on every run. After editing `.mcp.json`:

```
/doctor
```

If you see `[Failed to parse]` errors, the schema was violated. Check:

- No `_comment` or `_notes` fields anywhere
- Every server entry has exactly `command` (string), `args` (array of
  strings), and optionally `env` (object of strings)
- No extra top-level keys besides `$schema` and `mcpServers`
