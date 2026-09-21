# ADR-0030: Materializer follows opt-in content identities

- Status: Accepted
- Date: 2026-09-21
- Scope: Issue #54

## Context

Preserving authored identities exposed an unconditional `--require-content-identity` in
the public example materializer. It conflicted with ADR-0024 / Issue #44's optional pin
contract and made every unpinned example unusable.

## Decision

The example materializer follows the ordinary optional-pin contract. It validates supplied
pins but does not require absent pins, rewrite identities, or silently select strict CLI
mode. Deterministic SVG evidence remains a byte-reproduction requirement, independent of
whether inputs are pinned.

## Consequences

PR #53's full-pin conversion is not merged. The current unpinned examples remain canonical.
Strict closure verification, if introduced later, must be an explicit user-selected mode
with its own design and acceptance tests.
