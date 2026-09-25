# Design — P0, P1, and P2 Remediation Architecture (#454)

**Design plan:** `issue-454-p0-p1-p2-remediation-design-plan-2026-09-26.md`.
**Status:** proposed for architecture review.

## Current-state audit

The audit is against public `main` after #400, #449, and #410 closed.

| Issue | Confirmed current state | Design disposition |
| --- | --- | --- |
| #439 | Axis text is emitted before `axisBandDecoration`; inside labels are emitted after their mark loop but receive default text order.  Neither relationship is represented in completed Layout data. | New typed host-relative paint strata. |
| #443 | Axis labels use one collision domain per tier (`label-{tier_index}`); rotated bounds can cross lanes. | One axis-label collision domain and lane sizing from transformed bounds. |
| #435 | `missingActual` reaches `display_value(..., "text")`, which stringifies booleans. | Closed boolean table presentation at View ingress. |
| #445 | Group-detail and digest runs are single-line completed text despite narrow side slots. | Layout-owned wrapped block allocation and panel-height completion. |
| #448 | `FontMetricsCatalog` now selects exact declared `(family, weight)` values.  A released HALCYON Scene records the 700 asset identity for every sampled bold run.  Draft `--system-fonts` still rejects a Theme with more than one requested face. | Do not repeat the catalog work; design only multi-face draft resolution. |
| #376/#378 | #377 is closed and supplies draft preset ingress/default resolution.  Init still owns the corpus-sized first-run topology. | Reuse preset ingress; separate editable init sources from closure machinery. |

The audit confirms that the P0 defects are distinct missing authorities rather
than renderer bugs.  None can be fixed by reordering SVG strings, coercing a
value at an adapter, or allowing a Scene gate to repair output.

## Architecture decisions

### 1. Completed paint strata and hosts

`Layout` adds a finite paint-stratum vocabulary to completed placements:

```text
background < mark < hosted-text < foreground-text < annotation
```

A text placement that is semantically hosted by an axis band or a mark records
the stable host placement id and receives the corresponding `hosted-text`
stratum.  Axis bands are `background`; planned/actual/missing marks are
`mark`.  Non-hosted text retains a declared stratum based on semantic purpose.
The completed placement, not the Scene builder, determines the numeric paint
order from this finite relation.

Scene transports the resolved numeric order and optional `hostPlacementId`.
It does not derive a host by geometric overlap.  Adapter serialization keeps
its existing stable `(paint_order, input_index)` ordering and therefore cannot
reverse a declared host/text relation.  This repairs #439 structurally and
creates explicit input for #446's intentional-occlusion rule.

### 2. Axis layout is a single collision field

All axis label placements share `CollisionDomain("timeline-axis", "labels")`.
Before placing a tier, Layout computes its lane demand from its transformed
text bounds, including a 90-degree orientation.  The axis slot allocates
ordered lanes from those demands.  Inter-tier collision checking is then a
guard over completed geometry, rather than a substitute for lane allocation.

The existing explicit `visible-overflow` policy remains a completed fallback:
it can retain a label that does not fit the requested extent, but it cannot
turn an ordinary unmarked cross-tier overlap into a valid placement.  This
keeps #449's no-refusal policy while closing #443's silent collision gap.

### 3. Boolean values require a semantic display contract

Table columns whose source resolves to a boolean use a new finite `presence`
format.  Its View declaration supplies the two rendered alternatives and may
select a catalogued icon only through the existing icon capability path.  A
boolean source with `text` or an absent boolean presentation is a View ingress
diagnostic.  `display_value` receives a normalized finite presentation value;
it never calls `str` on boolean data.

The `missingActual` migration represents absence with the author-declared
missing marker and observation with the complementary declared value.  Its
semantic role remains `missingActualCell` only for missing state, so #431 can
validate its actual text paint separately.  The Scene contains ordinary
completed text/icon geometry and no boolean-specific renderer branch.

### 4. Side-panel paragraphs are measured blocks

Group detail and milestone digest content become measured block requests with
their owning side-panel slot's inline extent.  Layout wraps them using the
same selected font metric and typography treatment used to paint the text,
then allocates each panel's block extent from the completed lines plus
declared spacing.  If the requested panel cannot contain the block, the
existing visible-fit policy completes an expanded canvas and warning; it never
allows text to overprint an adjacent slot.

This is intentionally not a generic target clip.  The slot, line breaks,
bounds, warning, and canvas all exist before Scene construction.

### 5. Perceptibility is a Scene observation, not a policy engine

`check_scene_perceptibility` consumes only serialized Scene fields and emits
typed findings with a stable code, Scene path, primitive ids, and measured
facts.  Its four check families are occlusion, slot escape, text intersection,
and composited-paint contrast.  It observes completed paint order and host
relations; it cannot change an artifact.

Intentional host overlap is declared by `hostPlacementId`, not an unbounded
numeric allowlist.  The P0 corpus must be clean before the first checked
baseline is accepted.  Draft rendering runs the same evaluator after Scene
construction and emits warnings; immutable public evidence is checked by the
tool in CI.  #431 owns the contrast thresholds and role classification, while
#446 owns evaluator mechanics and reporting.

### 6. Feedback systems aggregate without changing product authority

Conformance is a maintainer orchestration layer: it executes every independent
gate, captures each result, prints a deterministic summary, and reports stale
derived documents with bounded unified diffs and the exact refresh command.
Pytest is a separate non-dependent CI job and the OS matrix does not
fail-fast.  This changes observability, not source validation semantics.

Presentation ingress gains an immutable aggregate diagnostic collection.
Schema violations are normalized, leaf errors replace composition wrappers,
and independent semantic checks join the same sorted list.  The first item
uses the established single-error rendering where a compatibility adapter
requires it; the command/report surface exposes the complete ordered set.

### 7. Release reviews map literal issue acceptance

The review template/convention has a required first table copied verbatim from
the issue acceptance list.  Each item has one of `met`, `deferred`, or
`narrowed` plus direct evidence.  Only all-`met` issues may close silently;
otherwise the issue remains open or its closing comment links the explicit
follow-up.  Programme-level criteria remain additional rows.

### 8. Contrast is classed, composited, and reproducible

The contrast policy has three finite classes: required body/state text,
optional decoration, and explicitly absent decoration.  Required text meets
the declared text floor; a decoration either meets its visibility floor after
compositing over its ground or is absent in the resolved Theme/Scene.

The quality report is generated from committed Scenes per semantic purpose.
It uses the same paint composition as the perceptibility evaluator, with
threshold selection remaining a color-scheme/Theme policy concern.  This
avoids a second renderer-specific contrast implementation.

### 9. Draft system fonts resolve a closed face catalog

The draft `--system-fonts` path resolves one exact system face for every
distinct Theme `(first family, weight)` request and constructs the same
`FontMetricsCatalog` abstraction used for declared Context resources.  It
keeps the resolved file paths solely as draft runtime state for SVG/PNG
rasterization.  A missing requested weight or family fails at closure; no
neighbouring face, generic family, or adapter fallback is permitted.

### 10. First-run sources, evidence, and closure have different roots

`chrona init` produces an editable minimal project and a named preset
reference.  An explicit example flag retains the corpus topology.  Generated
evidence and revision/store files reside in their declared generated or hidden
closure roots, not alongside the editable source tree.  README images are
manifest-reachable generated artifacts checked for byte identity.

The onboarding ladder is executable documentation over this topology and the
existing preset ingress.  It may not repurpose guided-authoring overrides as
design inheritance.  If Theme/View inheritance is necessary for its later
rungs, it receives a bounded separate design before implementation.

## Cross-cutting acceptance boundaries

- No P0/P1 implementation adds a renderer-local layout, font, format, paint,
  or fallback decision.
- P0 generated evidence is regenerated only after all linked source changes
  for that slice are complete; #446 baselines no known defect.
- Every newly declared value has schema, typed-contract, diagnostic inventory,
  and public materializer coverage before its issue is considered for closure.
- P2 removes unreachable artifacts only after the documentation/reference gate
  proves replacement reachability; history under `docs/archive/` stays intact.
