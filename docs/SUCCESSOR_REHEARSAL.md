# Successor Pickup Rehearsal

This is the repeatable, model-free rehearsal for a person taking over DueCare.
It complements the [maintainer handoff](MAINTAINER_HANDOFF.md), the
[30-day transition plan](PROJECT_TRANSITION_PLAN.md), and the private
[access-transfer receipt template](PRIVATE_TRANSFER_RECEIPT_TEMPLATE.md).

The automated rehearsal proves that a checked-out tree can establish current
state, validate the public and notebook surfaces, verify the durable archive,
and observe the paused engine. It does not prove that a human understands the
architecture or has received platform access.

## Run From A Fresh Shell

Use Python 3.12 with the repository development dependencies installed. Start
from a fresh clone or an intentionally preserved working tree; never erase
unknown changes to manufacture a clean result.

```powershell
$env:DUECARE_MAX_PLANNED_MODEL_CALLS='0'
py -3.12 scripts/rehearse_successor_pickup.py
```

The command runs five local steps in order:

1. handoff and live-pickup consistency;
2. the portable core publication gate;
3. active and optional notebook syntax and committed task-notebook cells;
4. checksum verification of every durable-archive member; and
5. a read-only autonomous-engine status observation.

It does not start Ollama, call a hosted model, access the network, publish an
artifact, remove the stop sentinel, or mutate benchmark results. The child
environment forces the planned-call ceiling to zero and enables offline modes
for common model libraries.

On the Windows host that owns the scheduled automation, follow the portable
rehearsal with this read-only host check:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/stop_ollama_stack.ps1 -Status
```

It must report the whole model/flywheel stack cost-stopped: five recurring
tasks disabled, four daemon sentinels present, and zero verified repository
daemon processes. The Python rehearsal observes the autonomous engine but
cannot portably inspect Windows Task Scheduler, so it does not replace this
host-specific check.

## Receipt

By default the command atomically writes the ignored file
`reports/handoff/successor_rehearsal.json`. The receipt contains:

- UTC generation time, Python version, branch, revision, and changed-path count;
- the exact local command label, exit status, duration, line count, and SHA-256
  of each command's combined output; and
- explicit zeroes for planned model calls, network calls, and publication
  actions.

Raw command output, absolute paths, credentials, names, email addresses, and
access details are not stored in the receipt. Use `--no-receipt` for a fully
read-only rehearsal. A receipt must stay below ignored `reports/`; the runner
rejects any other destination.

## Human Acceptance

After the automated command passes, the successor still needs to demonstrate:

- the active, optional, archived, experimental, and propose-only boundaries;
- one documentation-only change through review and rollback planning;
- one benchmark trace and one dataset-lineage trace end to end;
- an isolated archive restore, not only archive verification;
- the incident responses in the maintainer handoff; and
- private least-privilege access and recovery checks for each external
  platform.

Record platform ownership only in a private copy of the transfer template.
The public repository may record a dated category-level completion statement,
but never credentials, recovery answers, personal contact details, billing
data, or the location of secret material.

## Interpreting A Failure

A failed step or whole-stack status blocks transfer acceptance but is not
permission to change the claim boundary or resume model work. Reproduce the
smallest failing command,
compare live state with saved artifacts, fix the authoritative source, and run
the rehearsal again. A dirty tree is evidence to investigate, not a failure by
itself.

If no successor is available, use the maintenance-mode path in the transition
plan. An automated pass alone must never be represented as human acceptance or
completed account transfer.
