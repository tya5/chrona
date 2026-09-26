# Design — Total Fit Completion and Exact Host-Font Closure (#457, #447)

**Plan:** [issues-457-447-fit-and-host-font-design-plan](../planning/active/issues-457-447-fit-and-host-font-design-plan-2026-09-26.md).

## #457: normal-flow fit is not input validity

The accepted #449 rule applies before as well as after `SurfaceLayoutRequest`.
For a valid profile and nonzero viewport, the normal-flow solver must return a
finite `LayoutManifest`. Its requested viewport is a minimum allocation, not a
hard clipping boundary. Fixed tracks keep their declared size; content tracks
keep their measured minimum; flex tracks may shrink only to zero. If the sum
exceeds the available main extent, the children continue in deterministic
normal flow beyond the parent and Layout records a `W_LAYOUT_VISIBLE_OVERFLOW`
for each affected node with required and available inline/block extents. No
implicit proportional scaling changes Theme geometry.

In cross-axis and overlays, `strict` remains a placement preference, not a
fit-refusal mode. An unplaceable preferred position is emitted visibly at the
stable preferred coordinate with the same structured warning. `safe` clamps
only when a child fits; when the child itself exceeds the parent, it starts at
the parent's origin and overflows. An undeclared container overflow has this
visible disposition. Explicit slot policies (`ellipsize-with-source`,
`clip-optional`) retain their declared meaning; invalid profile structure,
references, impossible ratios, and nonpositive viewport still diagnose.

`LayoutManifest` carries typed fit warnings from normal-flow arrangement to
surface composition. The latter merges them with surface-level fit warnings,
completes the canvas from every emitted bounds/path, and passes both through
Scene. The CLI prints the ordered structured records after successful output.
No Scene or adapter geometry repair is allowed. Diagnostic messages for
remaining invalid layout input must identify the offending path/node and
relevant values; a bare fit code must not escape.

Axis fallback is a separate correctness error: a retained interval whose
label does not fit must carry `reason=visible-overflow` even when the View
requested thinning but thinning cannot produce a legal subset. Every retained
label remains emitted, with `W_LAYOUT_AXIS_OVERFLOW`; a malformed outcome still
diagnoses as invalid data. This rule aligns the result invariant with #449's
no-refusal fallback and does not silently delete an interval.

The migration is semantic, not schema-syntactic: `solve_layout` changes from
reject-on-fit to complete-and-warn for valid profiles. Its exact-fit output
must remain byte-identical; narrow-viewport Draft and immutable outputs may
grow their completed canvas and add warnings. Public default-size materializer
evidence must be compared for accidental changes.

## #447: one selected face across discovery, measurement, and paint

Draft font closure requests every distinct primary `(family, CSS weight)` in
the resolved Theme. An exact matching face already present in the packaged or
explicit declared metrics catalog takes precedence; the system resolver is
called only for missing pairs. The old prohibition on combining an explicit
`--font-metrics` catalog with `--system-fonts` is removed: the two inputs form
one exact draft catalog, with no substitution or nearest-weight fallback.
Immutable Contexts still reject volatile host discovery.

The fontconfig bridge converts CSS/OpenType weight to fontconfig's numeric
weight scale before calling `fc-match`. It requests file, family, weight, and
collection index, then verifies the selected `TTFont(fontNumber=index)`
against the requested CSS weight and English typographic family (name ID 16,
falling back to family ID 1). Localized records may precede English records;
the verifier checks all relevant records and keeps the requested English
family name for the exact closure. An absent face or substitution remains an
error; no fontconfig alias silently changes the selected Theme family.

A collection face is identified by its file-byte digest plus its face index
and logical `(family, weight)`. Distinct faces within one `.ttc` therefore do
not collide in the draft catalog even though they share source bytes. Metrics
are extracted from that selected face, not the collection default. PNG passes
the collection bytes only once to resvg with system fallback disabled; the
completed SVG family and weight select the same face from those bytes. A
collection PNG regression must inspect actual paint as well as metadata.
Host paths and collection index remain process-local, never serialized as an
immutable Context resource. Exact face identity in a Scene stays the source
byte identity already used by the metrics contract; the selected family and
weight disambiguate a collection face.

The first platform bridge remains fontconfig, as approved by #411. On a host
without `fc-match`, `E_FONT_SYSTEM_UNAVAILABLE` must explain that fontconfig
is needed and how to install it (Homebrew on macOS, package manager on Linux,
or a fontconfig installation on Windows). CoreText and DirectWrite are future
ports, not guessed filesystem scans. CI tests a real fontconfig-installed
single-file family; macOS additionally tests a real collection when available.

## Whole-architecture consistency

ADR-0031 and Specifications 08/33/50 still assign all physical completion to
Layout. #457 closes the pre-composition loophole in that owner, without adding
Scene repair. #447 stays above Layout in Draft closure, preserving #411's
volatile/immutable boundary and #448's exact multi-face catalog. Scene text
continues to carry completed family, weight, and asset identity; SVG and PNG
only serialize it. Neither change adds example-specific branches, renderer
measurement, or a compatibility rule that weakens the exact-face contract.

## Acceptance and migration review

The literal acceptance rows are in the design plan. Implementation must
exercise all corpus views at the three requested sizes and audit remaining
raise sites by reachability; test both draft and immutable ingress; inspect
generated SVG/Scene and warning extents. Host-font tests must include real
`fc-match`, selected TTC face metrics and PNG paint, English Hiragino naming,
and a missing-bridge action message. Any discovered conflict with these
rules requires a published design correction before code resumes.
