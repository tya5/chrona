# Issue 122 — Output Formats Implementation Plan

**Design authority:**
`docs/reviews/current/issue-122-output-formats-design-review-2026-09-22.md`
(PR #172).

## I122-1: Typed target/artifact contract and Context v0.7

- Replace the string-returning Renderer port with `RenderArtifact` bytes, media
  type, target kind, and adapter identity; add a presentation registry keyed by
  target kind.
- Add a strict `render-context-v0.7` schema for target kind/required
  capabilities and rasterizer environment identity.  Remove v0.6 schema/parser
  acceptance and migrate all public contexts, fixtures, tests, and materializer
  references atomically.
- Validate target capability requirements and rasterizer declarations before an
  artifact reaches CLI output.

**Acceptance:** fake renderer tests prove opaque artifact propagation; invalid
v0.7 target/rasterizer documents name stable schema/identity diagnostics; no
v0.6 context remains reachable.

## I122-2: Concrete SVG/Cairo adapters and unified CLI selection

- Adapt SVG serialization to return `RenderArtifact`; add a CairoSVG adapter
  for `png` and `pdf`, with exact CairoSVG/Cairo/DPI verification and stable
  missing/mismatch diagnostics.
- Add `--format svg|png|pdf` to draft `render`; it constructs the matching v0.7
  in-memory target.  Add optional assertion-only `--format` to `render-review`.
- Replace text-only output writing with artifact byte output.  No formatter
  branch may enter the review pipeline before renderer selection.

**Acceptance:** SVG byte fixtures remain unchanged; PNG/PDF have correct media
signatures and repeat under a pinned backend; invalid immutable format assertion
does not create an output; unavailable CairoSVG does not fall back to SVG.

## I122-3: Evidence and release gate

- Update test fakes, CLI/closure/use-case tests, schema/context fixtures, and
  public materializer invocation for v0.7.
- Run focused target tests, complete pytest, conformance, import/reachability
  checks, all five SVG materializers, and one batch of PNG/PDF fixture checks.
- Confirm generated SVG diff is empty and conduct a final architecture review
  against the design authority.

## Publication boundary

Implement these slices on one branch because Context migration, renderer port,
and both CLI paths must not leave a materializable context temporarily broken.
Publish one implementation PR only after all acceptance evidence is complete;
merge only after serial two-platform CI success, then close #122.
