# Issue #49 semantic presentation-contract refactor implementation plan

## Preconditions

The semantic-contract specification and architecture review are closed. This plan replaces further ad-hoc presentation recovery edits.

## Phase 1 — contract and registry

1. Add immutable `PresentationContract`, `LayoutPlacement`, and registry models.
2. Implement `normalize_presentation_input` at the public presentation ingress.
3. Implement contract validation for registry coverage and required theme bindings.
4. Add normalization and registry unit tests.
5. Publish the phase.

## Phase 2 — move geometry to Layout

1. Build measured table-column, row/group, track, axis, decoration, and routing placements in Layout.
2. Remove those calculations from `v05_builder`.
3. Add non-overlap and identity/track placement tests.
4. Publish the phase.

## Phase 3 — declarative Scene emission

1. Make Scene consume only `PresentationContract`, `LayoutPlacement`, and resolved canonical theme bindings.
2. Replace literal semantic role/token selections with registry lookup.
3. Preserve declared public primitive roles via registry entries.
4. Add purpose-coverage Scene tests for as-of, groups, axes, legend, annotations, and marks.
5. Publish the phase.

## Phase 4 — recovery closure and evidence

1. Re-run the original thirteen focused regressions against the refactored path.
2. Regenerate Controller Z and HALCYON evidence with the public materializer only.
3. Add manifest-context and byte-reproduction assertions.
4. Publish the phase.

## Phase 5 — external gate

Create a new external-verification issue for the complete pytest and materializer gate, because that execution is delegated. Its report must record exact commands, commit SHA, pass/fail counts, and generated-evidence status.

## Exit criteria

All #49 acceptance tests pass; every enabled semantic validates before render; no legacy Settings/Theme path, renderer branch, or hand-authored generated SVG is introduced.
