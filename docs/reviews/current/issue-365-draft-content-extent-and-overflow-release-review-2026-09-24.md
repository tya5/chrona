# Issue 365 release review

## Acceptance review

- Draft `WIDTHxauto` is typed at Draft ingress and resolves to a finite
  table-timeline viewport in Layout before Scene and renderer invocation.
- Fixed Draft overflow reports row count, row minimum, required/available
  extent, and a deterministic explicit `--viewport` value.
- Context validation and immutable fixed viewport behavior remain unchanged.
- The complete inert `layoutIntent` object (`compactness` and `itemStacking`)
  has been removed from schema, examples, conformance resources, gallery source snippets, and
  normative documentation.
- Integration curriculum exercises 30 and 100 generated rows for both fixed
  overflow and auto success; focused CLI, Layout, render, and closure-input
  acceptance tests pass.

## Structural review

The only new geometry decision is `resolve_draft_block_extent` in Layout.  Its
finite probe measures profile chrome; it does not render or inspect Scene
primitives.  The render use case orchestrates that resolver, while Scene still
receives a completed `LayoutManifest` and finite viewport.  Numeric detail is
preserved across Layout, Scene, render use case, and CLI.

## Verification

Full `pytest -q`, public materializer checks, generated SVG inspection, and
three-OS CI are release gates for this commit.  Their completed results are
recorded in the Issue before closure.
