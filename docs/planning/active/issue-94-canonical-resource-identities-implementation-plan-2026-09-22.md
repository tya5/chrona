# Issue 94 P94-4 — Canonical Resource Identities Implementation Plan

**Status:** Approved implementation plan. **Design authority:** Issue 94
completion plan and design review, merged at `a64f704` and amended at `683d672`.

## Scope

Replace the overloaded `chrona/presentation/v0.*` resource labels with one
canonical, kind-specific label.  The migration is atomic: examples, conformance
fixtures, schemas, closure/materializer checks, CLI tests, and normative current
specification examples change together.  No old label remains accepted.

| Kind / revision | Canonical version |
| --- | --- |
| Actual set v0.1 | `chrona/actual-set/v0.1` |
| Summary profile v0.1 | `chrona/summary-profile/v0.1` |
| Style v0.1 | `chrona/style/v0.1` |
| Theme v0.1 (historic fixture) | `chrona/theme/v0.1` |
| View v0.1 | `chrona/view/v0.1` |
| View v0.2 | `chrona/view/v0.2` |
| Render Context v0.6 | `chrona/render-context/v0.6` |

The retired Render Context v0.2 schema and federation fixture are not migrated:
they are removed because no current runtime accepts them.  Historic/archive
documents are not rewritten as current contracts.

## Steps

1. Replace the generic v0.1 resource schema with kind-specific schemas (or
   equivalent closed discriminators) and make every live validator require the
   canonical kind/version pair.  Add negative tests that reject the old shared
   label and a mismatched kind/version pair.
2. Rename all live example/conformance resources and exact-content references
   atomically.  Update public materializer and closure checks to require
   `chrona/render-context/v0.6`.
3. Remove the unreachable Render Context v0.2 schema and its federation
   conformance fixture rather than retaining a second accepted Context contract.
4. Update current specifications/examples that define a live format.  Preserve
   archive history without treating it as accepted input.

## Acceptance criteria

- Each live resource kind has exactly one accepted version label for its
  revision; an old `chrona/presentation/v0.*` label is rejected diagnostically.
- Closure validation verifies both kind and canonical version before Layout.
- The five materializer contexts use Render Context v0.6's canonical identity
  and byte-reproduce; expected SVG changes only if public bytes necessarily
  change (none are expected).
- Full pytest, conformance, reachability lint, and both CI platforms pass.

## Publication boundary

One implementation PR follows this plan. P94-5 starts only after it is merged.
