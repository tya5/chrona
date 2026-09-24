# Issue 370 identity producer design correction

**Status:** Accepted correction before I370-2 implementation

## Finding

The completed #369 command, `chrona workspace revision`, produces the
canonical identity of one validated authoring workspace.  It does not produce
the two other identity formats found by the declared-versus-computed inventory:

| Comparison family | Required identity |
| --- | --- |
| Immutable resource, font, icon, and materializer `contentIdentity` | SHA-256 of exact persisted bytes. |
| Replay request/target identity | Core canonical JSON identity of a parsed document. |
| Guided workspace `baseRevision` | Canonical identity of a validated authoring workspace. |

Treating these as one generic hash would be incorrect: byte identity and
canonical document identity intentionally differ for semantically equal YAML
with different bytes, while workspace identity additionally validates its
specific contract.

## Decision

Add a read-only CLI adapter over existing identity codecs:

```text
chrona identity bytes PATH
chrona identity document PATH
```

Both commands print exactly one `sha256:<digest>` plus a newline.

- `identity bytes` reads `PATH` as opaque bytes and computes the same raw-byte
  SHA-256 used by immutable `contentIdentity` pins.
- `identity document` parses a YAML/JSON document with the existing safe
  loader, converts it through Core `json_value`, and computes Core
  `content_identity`.  It does not guess a resource schema, perform network or
  Store I/O, or mutate input.
- `workspace revision` remains separate.  It validates and reads an
  authoring workspace before using the same Core codec; it is not an alias for
  arbitrary document identity.

`identity bytes` is the producer named by resource/font/icon/materializer pin
classifications.  `identity document` is the producer named by replay
request/target classifications.  The existing workspace command resolves the
sole product-bookkeeping `baseRevision` classification.

## Architecture review

| Boundary | Decision |
| --- | --- |
| Core identity | Reuse `content_identity` without a second canonical serializer. |
| Byte pins | CLI computes exactly the raw SHA-256 already asserted by the owners. |
| CLI | Read-only adapter; it owns paths, stdout, and diagnostic envelopes only. |
| Use cases/Store/closure | Unchanged; no user command can rewrite a pin or bypass a verification assertion. |
| Workspace | Retains its validated, authoring-specific read path. |

The command exposes existing evidence formats; it does not make hashes a new
source of authority or introduce compatibility aliases.

## Required implementation-plan update

I370-2 adds focused tests for exact byte identity, canonical document identity
across formatting-only YAML changes, malformed document diagnostics, and the
distinct workspace revision behavior.  It documents both commands and assigns
all nine inventory rows exactly once before enabling the check.
