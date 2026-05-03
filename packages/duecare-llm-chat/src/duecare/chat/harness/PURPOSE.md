# Harness — purpose

**Module id:** `duecare.chat.harness`

## One-line

Default safety-harness layers for the Duecare chat playground.

## Long-form

Default safety-harness layers for the Duecare chat playground.

Ships GREP rules, RAG corpus, Tools data + dispatcher, and a
`default_harness()` factory that returns all callables and catalogs
ready to pass to `duecare.chat.create_app(**default_harness())`.

Architecture: keeping the safety content here (in the chat wheel)
rather than inline in each kernel.py keeps kernel.py minimal, lets
content version with the wheel, and makes the chat-playground +
chat-playground-with-grep-rag-tools notebooks share the exact same
safety surface (the toggle notebook just enables it via toggles).

## See also

- [`AGENTS.md`](AGENTS.md) — agentic instructions for AI readers
- [`HIERARCHY.md`](HIERARCHY.md) — position in the module tree
- [`STATUS.md`](STATUS.md) — completion state and TODO list
