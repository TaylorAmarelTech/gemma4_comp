# A-16 — Knowledge-pack builder + verifier

<!-- duecare:lane-label -->
> **Serves lanes:** 04 Researcher, 05 Developer / integration partner

## Status

**Folder reserved; kernel.py pending.** This slot will:

1. Accept a list of public-source URLs / files for a corridor pack
2. Build a versioned pack manifest with content + curator metadata
3. Sign the pack with a deterministic hash (sha256 over content +
   manifest)
4. Verify pack pull: simulate a researcher running
   `duecare-cli pack pull <slug>@<version>` and verify the hash
   matches the signed manifest
5. Emit `<pack_slug>-v<version>.tar.gz` + signed manifest as the
   bundle output

Closes the "researcher reproducibility" gap (the website's
`knowledge-packs.html` + `client-connect.html` mechanics).

See `docs/appendix_experiment_ladder.md` for the full ladder spec.
