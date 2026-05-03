# INPUTS / OUTPUTS — `duecare.agents.evolution`

This file documents the protocols and context keys this module reads from and writes to. Auto-stamped — fill in specifics as the module's contract solidifies.

## Reads

- Configuration via constructor arguments (typed via Pydantic v2)
- Optional context dict (see `duecare.core.contracts`)

## Writes

- Return values typed via Pydantic v2 schemas where applicable
- Side effects (file writes, DB writes, network calls) are explicit in each function's docstring

## Protocols implemented

See `duecare.core.contracts` for the protocol definitions this module satisfies.
