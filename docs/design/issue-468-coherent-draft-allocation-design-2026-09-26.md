# Design — Coherent Table-Timeline Allocation and Starter Gate (#468)

## Selected behavior

For a valid table-timeline closure, the requested finite viewport is the
**minimum** profile allocation, not a hard clip. Layout computes its measured
content requirement before final placement. If the timeline host is too
short, Layout re-solves the **whole profile** at the least finite block size
that gives that host its required extent. Thus `review-surface`, `table` and
`timeline` grow together and normal-flow successors such as `notes` move
below them. The completed canvas may still expand around other legitimate
visible-overflow placements; canvas expansion is not a substitute for
allocating a known row/track requirement. An explicit `1600x900` remains a
minimum 900-high request; if its content fits, its output stays 900 high.
No special case depends on HALCYON-1, row IDs or a preset.

## Layout ownership and algorithm

Replace the Draft-only extent helper with a Layout-owned content-allocation
resolver. Inputs are a resolved profile, finite requested inline/block
extents, source measurements and a finite map of source-specific required
block extents (currently `timeline`). It probes one normal arrangement,
measures profile chrome from the allocated source, and computes the smallest
block extent satisfying the source requirement. A final `solve_layout` uses
that extent and yields one coherent `LayoutManifest`; surface composition
consumes it unchanged. The resolver must check final source allocation and
may make a bounded deterministic correction for rounding. If a valid
fixed/max profile cannot give the host more space, #449's visible fallback
remains truthful and records its shortage; invalid profile structure alone
is an error. The resolver cannot
silently add pixels in Scene or an adapter. Requirements must be derived from
the same measured track/row/mark geometry as placement. A real residual fit
failure still completes visible geometry and structured warnings under #449.

This rule applies to table-timeline Drafts and immutable Contexts alike,
because both share Layout's completed geometry contract. Non-table surfaces
retain their existing finite allocation and visible-fallback behavior until
they declare their own content requirement. `WIDTHxauto` remains a Draft-only
request syntax, and does not enter immutable Contexts. It selects a finite
content-sized Layout allocation using the same resolver; it is no longer a
separate reflow algorithm. A fixed request and an auto request can therefore
produce the same completed height when content requires it.

## Draft defaults and axis

The bare `render` CLI, `render-workspace` CLI, guided render ingress and typed
Draft APIs default to `(1600, None)`, represented by CLI `1600xauto`. An
explicit finite Draft viewport remains accepted. The synthetic Draft Context
retains a finite 900-high seed solely for schema-valid closure; Layout
resolves it before Scene and no `auto` token is persisted to an immutable
Context.

The bundled `chrona-default-draft` View declares a quarter band and a month
labels tier with finite forms and `thin-with-record` fitting; the month tier
is selected independently of the Context locale through the already
published name-table rule. At ordinary 1600-wide HALCYON-1, completed SVG
must visibly carry at least one month text primitive. Axis geometry remains
Layout-owned and no new schema syntax is needed. The View resource change is
an intentional source identity change; copied presets obtain the new View
bytes, while previously copied user Views are not silently rewritten.

## Perceptibility release gate

Keep #446's one pure serialized-Scene evaluator. Add a starter-render
conformance entry that renders the actual bundled default Draft against the
HALCYON-1 project, serializes its completed Scene, then passes the mapping to
that evaluator. Any `E_` finding, including `E_SCENE_TEXT_INTERSECTION`,
fails the gate; warnings from the Draft CLI remain supplementary feedback,
not a bypass. The committed-scene gate remains unchanged. A fixture that
introduces a measured text-text intersection must fail the same starter
gate. User-visible acceptance also inspects actual SVG month text and note
placement; Scene findings alone are not proof of SVG correctness.

## Adjacent architecture and migration

This completes #449's intended review-surface extension instead of weakening
its no-refusal rule. It preserves #365's finite Draft auto resolution, #446's
observer-only evaluator, Specification 33's Layout geometry authority,
Specification 08's completed Scene transport, Specification 50's typed
fallback semantics and ADR-0031. No View/Layout Profile schema changes or
compatibility reader are needed. Expect possible intentional Scene/SVG
geometry changes for public Contexts whose known row requirements previously
escaped their allocated hosts; regenerate and inspect all affected public
materializers as one batch, including actual rendered SVGs. Invalid profiles,
missing sources and integrity errors remain errors; an ordinary fit shortage
never becomes a render refusal. Notes and table text must not intersect after
the structural reallocation, and every completed primitive remains inside
the completed canvas.
