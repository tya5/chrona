# Issue #38 reproducible example closure specification

## Authoring and execution boundary

Render Context v0.5/v0.6 may keep `contentIdentity` optional in source authoring. The public example materializer is the immutable-closure boundary: before invoking `render-review`, it derives a temporary Context whose every copied resource reference carries the SHA-256 of the exact copied bytes, then invokes the CLI with `--require-content-identity`.

This repairs stale or omitted source hashes without silently weakening execution-time verification. The derived Context reference already follows the same rule.

## Context selection

For each manifest slide, `slides[].context` selects the context; manifest-level `context` is only the compatibility fallback. All selected contexts are copied and derived independently.

## Acceptance

- v0.5 and v0.6 context schemas are selected from the version suffix without literal escape corruption.
- Source examples validate structurally.
- A stale or missing source reference identity cannot bypass the materialized closure: the derived reference must contain the exact byte identity.
- Every manifest slide is materialized through the public CLI and compared with its tool-generated expected SVG.

## Compatibility

Existing authoring contexts remain valid. Settings/legacy Theme contracts are not restored.