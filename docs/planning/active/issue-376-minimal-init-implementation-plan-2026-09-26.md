# Implementation Plan — Minimal `chrona init` and Explicit Corpus Example (#376)

**Design:** `issue-376-minimal-init-design-2026-09-26.md`.
**Architecture review:**
`issue-376-minimal-init-architecture-review-2026-09-26.md`.

## I376-1 — Typed templates and init-mode boundary

Add the wheel-owned three-file minimal template and a dedicated resource
accessor.  Change the CLI and `initialize_project` so no example selects it,
while `--example halcyon-1` selects the named manifest-bearing corpus.  Retain
non-overwrite and unsupported-example diagnostics.  Add unit and CLI tests for
the exact starter topology, YAML validity, public no-preset draft rendering,
and explicit named-example selection.

**Acceptance:** default initialization creates only editable starter source;
the README command renders it; an explicit HALCYON request still copies the
full source rather than receiving the starter.

## I376-2 — Hide explicit-example immutable Store state

Route the full-example `copy_context_closure` target to `.chrona/store` and
write its Store configuration with that root.  Assert all revision directories
are below the Store root, Context resolution succeeds from that configuration,
and no root-level `revision-*` directory is created.  Do not alter Context
reference identity, materializer behavior, or corpus source paths.

**Acceptance:** the explicit example remains fully Store-resolvable and has no
generated closure beside its source; source-to-closure copying remains
deterministic and identity-checked.

## I376-3 — First-run documentation and release gate

Replace the root README default-init path, add the focused smallest-project
guide, and regenerate the CLI reference.  Add documented-command coverage for
the starter render and review its SVG once.  Run focused init/resource/CLI
tests, the public materializer suite, conformance, generated-document checks,
and `git diff --check`; inspect generated SVG differences.  Observe remote CI
once after the final material commit.

**Acceptance:** a newcomer can follow the checked-in README/guide from empty
directory to a Draft SVG, and the explicit corpus path/documentation remains
accurate.  Publication is one coherent feature commit after all slices pass.
