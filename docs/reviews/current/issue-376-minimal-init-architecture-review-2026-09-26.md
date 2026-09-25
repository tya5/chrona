# Architecture Review — Minimal `chrona init` (#376)

**Decision:** Accepted for implementation planning.

The proposed split preserves the repository's authority boundaries.  The
minimal template is editable Draft input and consumes the already-typed #377
default only at draft-render ingress.  It neither creates a Context nor claims
materializer reproducibility.  Conversely, the full HALCYON route remains a
manifest/Context corpus, with a configured immutable Store; relocating its
revision directories below `.chrona/store` changes only the filesystem adapter
root and does not make mutable source a Store fallback.

Template identity is kept separate from corpus identity by a dedicated package
resource accessor.  CLI selection stays a thin adapter; local-authoring owns
the mode decision and closure preparation; materialization and rendering do not
acquire `init` policy.  The result is compatible with the existing packaged
default, Store discovery, Context closure, and example-evidence architecture.

The planned intentional public change is accepted: no flag means a minimal
starter, and the complete corpus requires `--example halcyon-1`.  No legacy
alias is needed because it would preserve the ambiguous product boundary this
issue removes.
