# Implementation Plan — Visible Row-Density Policy (#400)

**Design:** `dc9030d3`, `b8106a82`.
**Architecture review:** this directory's
`issue-400-visible-row-density-architecture-review-2026-09-25.md`.

## I400-1 — Profile and typed outcome contract

Create Layout Profile v0.9 with required finite `rowDensity` policies; migrate
all live profiles/Contexts and delete the v0.8 reader.  Add typed failure and
row-density outcomes to the Layout closure, plus a finite
`rowDensityClip` capability.  Add schema, contract, policy-completeness, and
negative migration tests.

**Acceptance:** every live profile declares both policies; no generic slot
overflow is consulted for row density; v0.8 is rejected; an outcome cannot be
constructed without policy, extent facts, and row identities.

## I400-2 — Layout compaction and completed clip placement

Make the render preflight and `place_rows` consume the same explicit outcome
resolver.  Preserve P1 requirements and ordinary containment; on selected
compaction, allocate deterministic proportional row heights, create row clip
hosts, attach completed mark/table-text clips, and emit exactly one structured
warning.  Keep diagnose behavior with actionable required/available detail.

**Acceptance:** fixed draft compaction retains all row/item identities and
clips only at its completed host; ordinary mark-containment negative still
fails; `diagnose` fails; stable same-input placement/warning bytes pass.

## I400-3 — Projection, target admission, and author warning

Project outcome and clip hosts through Scene.  SVG/PNG/PDF admission must
serialize completed clipping; Typst/TikZ reject `rowDensityClip`.  Emit draft
structured warnings through the CLI without making immutable evidence depend
on stderr.  Add structural tests that Scene/adapters never resolve policy or
derive a clip.

**Acceptance:** SVG/PNG visual fixture shows row-bound clipping; Scene has no
host path or adapter policy; unsupported targets reject honestly; draft stderr
contains the structured warning.

## I400-4 — Evidence and release

Add explicit compact and diagnose corpus/profile fixtures, regenerate affected
public materializers in one batch, and review SVG/PNG differences.  Run
focused tests, full pytest, conformance, every public materializer,
documentation/structural/coverage gates, wheel smoke, and three-platform CI.
Publish an English acceptance review before closing #400.

No I400 slice may weaken mark containment globally, retain the old fixed-draft
preflight, or add a compatibility reader.
