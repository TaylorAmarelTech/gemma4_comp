# Extensions — purpose

**Module id:** `duecare.chat.extensions`

## One-line

Duecare extension-pack client.

## Long-form

Duecare extension-pack client.

Loads installed packs (verified, signed bundles per
`docs/extension_pack_format.md`) and merges their content into the
in-memory harness catalogs. Built-in rules + RAG docs + tools shipped
in this wheel stay frozen; packs are additive.

Entry point:

    from duecare.chat.extensions import ExtensionPackClient

    client = ExtensionPackClient(
        registry_url="https://tayloramareltech.github.io/duecare-extension-packs/",
        cache_dir=Path("~/.duecare/packs").expanduser(),
        trust_root_path=Path("~/.duecare/trust_root.json").expanduser(),
    )

    # List what the registry offers
    available = client.list_available()
    # Install a specific pack (downloads + verifies + caches)
    pack = client.install("ph-hk-domestic-2026-q2", version="1.2.0")
    # Get the merged catalog
    grep_rules = client.merged_grep_rules()
    rag_docs = client.merged_rag_docs()

The harness module exposes `merge_extension_packs(pack_paths)` to
splice loaded pack content into `GREP_RULES`, `RAG_CORPUS`, etc.
without forcing every consumer to know about the extension system.

## See also

- [`AGENTS.md`](AGENTS.md) — agentic instructions for AI readers
- [`HIERARCHY.md`](HIERARCHY.md) — position in the module tree
- [`STATUS.md`](STATUS.md) — completion state and TODO list
