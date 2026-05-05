# Duecare Extension Pack Format (v1)

A signed bundle of GREP rules, RAG documents, lookup-tool entries,
classifier examples, and prompt tests that any Duecare deployment
(chat playground, classifier dashboard, Android app, custom
integration) can optionally pull and merge into its local catalog —
without rebuilding the wheel or republishing the APK.

> **Status (2026-05-01):** v1 spec frozen. Reference builder at
> `scripts/build_extension_pack.py`. Reference signer at
> `scripts/sign_extension_pack.py`. Pull-side client integration in
> `packages/duecare-llm-chat/src/duecare/chat/extensions/`. Public
> registry hosted at `https://tayloramareltech.github.io/duecare-extension-packs/`
> (gh-pages branch of a separate registry repo, planned).

## Why this exists

The corpus is a moving target — laws change (POEA MCs are issued
annually, kafala reform in 2024 invalidated several previously-valid
rules), case precedents accumulate, NGO contacts churn. A v0.6 APK
released today would have stale rules in 6 months unless the user
manually updates the app.

Extension packs decouple **rule content** from **app version**:

- A POEA officer can publish a v2026-Q3 update covering new
  Memorandum Circulars without touching any of our code.
- An IJM analyst can publish a corridor-specific pack for, say,
  ID→TW (Taiwan domestic worker) that we don't ship by default.
- A research team can publish a benchmark pack with their own
  prompt tests.
- Apps in the field can pull updates over Wi-Fi, verify the
  signature, and merge — never running unverified code.

## Three core principles

1. **Signed bundles only.** Every pack ships with a detached
   signature from one of a small set of authorized signing keys
   (Ed25519). Clients reject unsigned or wrong-key packs.
2. **Additive, never destructive.** A pack adds rules / docs /
   tools / examples. It does NOT remove or modify built-in rules
   shipped with the wheel — those stay frozen at the wheel's
   release. Packs that need to "supersede" a built-in rule do so
   by adding a higher-priority duplicate; the worker can disable
   the built-in via the in-app catalog UI.
3. **Opt-in pulls, no push.** Clients pull updates only when the
   user explicitly opts in (Settings → "Check for updates"). No
   background sync, no auto-install, no telemetry. The registry
   server only serves; it never receives.

## Pack file structure

A pack is a single `.tar.gz` archive containing:

```
duecare-pack-<id>-v<semver>/
├── manifest.json           <- pack metadata + included content list
├── content/
│   ├── grep_rules.jsonl    <- 0+ GREP rules in the same shape as
│   │                          packages/duecare-llm-chat/.../GREP_RULES
│   ├── rag_corpus.jsonl    <- 0+ RAG docs in the same shape as RAG_CORPUS
│   ├── tools.jsonl         <- 0+ corridor cap / NGO / fee-camouflage entries
│   ├── classifier_examples.jsonl  <- 0+ classifier example prompts
│   └── prompt_tests.jsonl  <- 0+ prompt tests with graded responses
├── changelog.md            <- human-readable changelog
└── README.md               <- description + usage guide
```

Plus a sibling `duecare-pack-<id>-v<semver>.sig` file containing the
detached Ed25519 signature.

## manifest.json schema

```json
{
  "schema_version": "1.0",
  "pack_id": "ph-hk-domestic-2026-q2",
  "pack_version": "1.2.0",
  "pack_title": "PH→HK Domestic Worker Updates (2026 Q2)",
  "pack_description": "Adds POEA MC 02-2026 + new MfMW HK hotline + 4 GREP rules covering recent recruitment fraud variants observed in Q1 2026.",
  "license": "MIT",
  "publisher": {
    "name": "Mission for Migrant Workers HK",
    "contact_url": "https://www.migrants.net/",
    "signing_key_id": "ed25519:abc123..."
  },
  "scope": {
    "corridors": ["PH-HK"],
    "stages": ["PRE_DEPARTURE", "EMPLOYED"],
    "languages": ["en"]
  },
  "issued_at": "2026-04-30T12:00:00Z",
  "expires_at": "2027-04-30T12:00:00Z",
  "supersedes": [
    "ph-hk-domestic-2026-q1@1.0.0"
  ],
  "depends_on": [],
  "content": {
    "grep_rules": 4,
    "rag_corpus": 3,
    "tools": 2,
    "classifier_examples": 5,
    "prompt_tests": 12
  },
  "checksum_sha256": {
    "manifest.json": "<self-reference excluded from checksum>",
    "content/grep_rules.jsonl": "abc...",
    "content/rag_corpus.jsonl": "def...",
    "content/tools.jsonl": "ghi...",
    "content/classifier_examples.jsonl": "jkl...",
    "content/prompt_tests.jsonl": "mno..."
  }
}
```

### Field requirements

| Field | Required | Validation |
|---|---|---|
| `schema_version` | yes | exact match `1.0` |
| `pack_id` | yes | regex `[a-z][a-z0-9-]{2,49}`; globally unique |
| `pack_version` | yes | semver |
| `publisher.signing_key_id` | yes | must match a key in the trust root (see below) |
| `scope.corridors` | optional | restricts pack visibility to apps configured for these corridors |
| `expires_at` | yes | clients warn after, refuse to merge after +30 days |
| `supersedes` | optional | clients silently replace older packs with same `pack_id` |
| `depends_on` | optional | other packs this pack assumes are installed; client refuses merge if missing |
| `checksum_sha256` | yes | clients re-compute and verify |

## Signing

Detached Ed25519 signature over the SHA256 of the entire `.tar.gz`
archive (NOT just the manifest — protects against pack-file
tampering).

```bash
# Sign (publisher side)
python scripts/sign_extension_pack.py \
    --pack ph-hk-domestic-2026-q2.tar.gz \
    --private-key ~/.duecare/keys/mfmw-hk.ed25519 \
    --output ph-hk-domestic-2026-q2.tar.gz.sig

# Verify (client side)
python scripts/verify_extension_pack.py \
    --pack ph-hk-domestic-2026-q2.tar.gz \
    --signature ph-hk-domestic-2026-q2.tar.gz.sig \
    --trust-root ~/.duecare/trust_root.json
```

### Trust root

A small JSON file that ships with each Duecare release listing
authorized signing keys + their authorities:

```json
{
  "schema_version": "1.0",
  "issued_at": "2026-05-01T00:00:00Z",
  "next_rotation_at": "2027-05-01T00:00:00Z",
  "keys": [
    {
      "key_id": "ed25519:abc123...",
      "publisher": "Taylor Amarel (Duecare maintainer)",
      "authority": "all",
      "valid_from": "2026-05-01T00:00:00Z",
      "valid_until": "2028-05-01T00:00:00Z"
    },
    {
      "key_id": "ed25519:def456...",
      "publisher": "Mission for Migrant Workers HK",
      "authority": "corridors:PH-HK,ID-HK",
      "valid_from": "2026-06-01T00:00:00Z",
      "valid_until": "2027-06-01T00:00:00Z"
    }
  ]
}
```

The trust root itself is signed by the Duecare maintainer (root key
is offline; rotation requires a Duecare release). Clients refuse to
merge a pack whose signing key isn't in the trust root, even if the
signature itself is cryptographically valid.

## Registry layout

A static GitHub Pages site (or any static host):

```
https://tayloramareltech.github.io/duecare-extension-packs/
├── index.json              <- list of all available packs
├── packs/
│   ├── ph-hk-domestic-2026-q2/
│   │   ├── 1.0.0.tar.gz
│   │   ├── 1.0.0.tar.gz.sig
│   │   ├── 1.1.0.tar.gz
│   │   ├── 1.1.0.tar.gz.sig
│   │   ├── 1.2.0.tar.gz
│   │   └── 1.2.0.tar.gz.sig
│   └── ...
└── trust_root.json         <- signed by the Duecare maintainer key
```

`index.json` is a small file (~50 KB even with hundreds of pack
versions) listing every pack id + version + manifest URL + signature
URL + signing-key id. Clients fetch this once, then GET any specific
pack manifest + content on demand.

## Client-side merge

```python
from duecare.chat.extensions import (
    ExtensionPackClient,
    InstalledPack,
    PackTrustError,
)

client = ExtensionPackClient(
    registry_url="https://tayloramareltech.github.io/duecare-extension-packs/",
    cache_dir="~/.duecare/packs",
    trust_root_path="~/.duecare/trust_root.json",
)

# Refresh the registry index
available = client.list_available()

# Download + verify + merge a specific pack
try:
    pack = client.install("ph-hk-domestic-2026-q2", version="1.2.0")
    print(f"Installed {pack.id} v{pack.version}: "
          f"+{pack.content.grep_rules} GREP rules, "
          f"+{pack.content.rag_corpus} RAG docs, ...")
except PackTrustError as e:
    print(f"REFUSED: {e}")  # signature invalid, key not in trust root, etc.

# Use the merged catalog
from duecare.chat.harness import GREP_RULES, RAG_CORPUS
# These now include both built-in + installed pack content
```

The Android app's Settings → "Updates" tab calls the same client
through a Kotlin port, with progress + verification status surfaced
to the worker before they accept the merge.

## What this enables

**For NGO partners:**

- Publish corridor-specific updates without us having to coordinate
  a release. MfMW HK can ship `ph-hk-domestic-2026-q2.tar.gz` with
  one command + their key.
- Trial new GREP rules in the field; if accurate, contribute back to
  the canonical bundle in a future release.

**For workers / NGO clients:**

- Pull only the corridors that apply to them. A Filipino DH in
  HK doesn't need the Saudi MoHR pack.
- Stay current as laws change without reinstalling the app.
- Verify the source: the install confirmation dialog names the
  publisher + key + scope.

**For research:**

- Ship benchmark packs (the existing 21K-test trafficking benchmark
  could be packaged as one).
- Compare Gemma 4 stock vs Gemma 4 + a specific extension pack via
  the rubric system.

## Security posture

- **Compromise of a publisher key** → only that publisher's packs
  are affected. The trust root scopes each key by authority
  (`corridors:`, `all`, `benchmark`, etc.).
- **Compromise of the registry server** → cannot push malicious
  packs (clients verify signatures against trust root regardless
  of source). Worst case: registry serves a denial-of-service.
- **Compromise of the trust root** → catastrophic. Trust root is
  rotated annually; root key is held offline (hardware token or
  air-gapped machine).
- **No trust by transitive dependency.** A pack's `depends_on`
  doesn't auto-install the dependency; the client requires the
  worker to install each pack explicitly.
- **Replay protection.** `expires_at` + per-version monotonic
  ordering prevents an attacker from serving a stale-but-validly-
  signed pack to override a fix.

## Lifecycle / governance

| Stage | Owner |
|---|---|
| Spec change (this doc) | Duecare maintainers + 1 NGO partner sign-off |
| New publisher onboarding | Duecare maintainer issues key after vetting; trust root release within 7 days |
| Pack publishing | Publisher self-serves (signed PR to registry repo, auto-merged after CI lint passes) |
| Pack revocation | Trust root update revokes key + emergency Duecare release advises clients to refresh |

## What this is NOT

- Not a way to push code to apps. Packs contain DATA only — JSON
  records consumed by existing harness loaders. No executable,
  no Python eval, no JavaScript, no JNI.
- Not a telemetry channel. Registry serves; it never receives.
- Not a payment / subscription system. Free for any non-commercial
  use; commercial use requires explicit license per the MIT terms.
- Not a substitute for the canonical bundle. Built-in rules in the
  wheel are the floor; packs are additive. A client with no packs
  installed still has the full 49 GREP / 33 RAG / 5 tools / 394
  prompts that ship today.

## See also

- `scripts/build_extension_pack.py` — reference pack builder
- `scripts/sign_extension_pack.py` — Ed25519 signer
- `scripts/verify_extension_pack.py` — verifier (used by clients + CI)
- `packages/duecare-llm-chat/src/duecare/chat/extensions/` — Python client integration
- `docs/research_server_architecture.md` — the future continuous-research server that auto-generates packs
