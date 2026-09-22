# Issue 94 P94-5 — Complete Surface Content Implementation Plan

**Status:** Approved implementation plan. **Design authority:** Issue 94
completion plan, merged at `a64f704`.

## Problem

`SurfaceContentInput` is the authoring-to-Layout input boundary, but every field
currently has a default.  A dropped normalizer field can therefore become an
empty Scene family and look like valid output.  Direct unit callers also use an
empty constructor, obscuring the required minimal contract.

## Closed contract

The following are required at construction: `table_columns`, `table_cells`,
`relations`, `annotations`, `show_member_labels`, label/relation/group policy,
axis policy, as-of facts/label, annotation policy, calendar, notes, legend,
coverage, summary/template/group/milestone/observation values.  Each is supplied
explicitly by the normalizer or a test fixture.  An empty tuple/string/`None`
remains a valid declared absence; omission is not valid.

`SurfaceContentInput` has no fallback construction path.  `normalize_v05_surface_content`
is the sole public materializer construction route.  Tests may create an
explicit minimal complete input through a local helper, never `SurfaceContentInput()`.

## Steps

1. Remove defaults from `SurfaceContentInput` without changing types or the
   normalized semantics of any field.
2. Update all unit fixtures to name every field, using a single explicit
   minimal-input factory where it makes the intended absence readable.
3. Add negative construction coverage proving that omitted required inputs
   raise `TypeError`, and public-path coverage proving normalizer output remains
   complete.
4. Run focused model/Scene tests, full pytest, conformance, reachability lint,
   five materializer byte checks, and generated SVG diff.

## Acceptance

No `SurfaceContentInput()` or partial construction remains.  A public
materializer still receives exactly one normalizer-produced complete value;
Layout/Scene behavior and expected SVG bytes are unchanged.

## Publication boundary

One implementation PR follows this plan. P94-6 begins only after it merges.
