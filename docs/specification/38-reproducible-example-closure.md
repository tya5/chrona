# Issue #38 reproducible example closure specification

## Authoring and execution boundary

Render Context source authoring keeps `contentIdentity` optional, and the public examples carry none (Specification 42, Issue 1567). The public example materializer is the immutable-closure boundary: it copies every referenced resource byte-for-byte, computes the SHA-256 of the exact copied bytes itself, and records that computed identity in the generated evidence and in the Context reference it renders. An authored pin is verified against the copied bytes and a mismatch fails; an absent pin is not an error and is never backfilled into the authored file.

The derived Context reference already follows the same rule.

## Context selection

For each manifest slide, `slides[].context` selects the context; manifest-level `context` is only the compatibility fallback. All selected contexts are copied and derived independently.

## Acceptance

- v0.5 and v0.6 context schemas are selected from the version suffix without literal escape corruption.
- Source examples validate structurally.
- A stale or missing source reference identity cannot bypass the materialized closure: the derived reference must contain the exact byte identity.
- Every manifest slide is materialized through the public CLI and compared with its tool-generated expected SVG.

## Compatibility

Existing authoring contexts remain valid. Settings/legacy Theme contracts are not restored.