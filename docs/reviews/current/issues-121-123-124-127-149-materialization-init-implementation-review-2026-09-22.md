# Materialization and Local Initialization — Implementation Review

## Scope

P5 / issue #121: public immutable materialization, deterministic store
discovery, and safe local project initialization.

## Result

The application service owns manifest selection, immutable closure copying,
authored identity checks, render execution, and declared artifacts. The old
tool is now a developer wrapper. `chrona materialize` uses the service directly
instead of a subprocess.

`chrona init` creates the live `halcyon-1` resource set and one
`.chrona/store.yaml` only in an empty/new target. It never replaces an
authored target. Store discovery accepts only an explicit config or a
project-local `.chrona/store.yaml` found by walking upward; no home-directory
or broad-directory fallback exists. Explicit config takes precedence.

## Boundary review

CLI owns argument parsing, diagnostics, and output-path selection. Application
services own materialization and authoring operations; renderer, closure, and
storage boundaries are unchanged. The materializer continues to verify an
authored content identity where one is declared, while contexts that omit an
optional identity remain materializable.

## Verification

Focused CLI/materializer checks, precedence/no-store/no-overwrite tests, and a
fresh initialized project materialization are required before publication.
