# Issue 86 — Summary Profile Completion Design Review

**Reviewed baseline:** `569f484abe72b42dd4c79254a06ca6a895007d5b`
**Design-plan authority:** `issue-86-summary-profile-completion-design-plan-2026-09-22.md`

## Decision

Issue #86 is approved as a narrow, behaviour-correcting completion of the
existing review pipeline.  A bound summary profile becomes one immutable,
normalized **SummaryContent** value before source measurement.  Its ordered
text runs are the single authority for both source measurement and Layout text
placement.  The final `SurfaceContentInput` carries that same value; it is not
a partial input and is still constructed only after the manifest-dependent
detail facts are available.

```text
typed SummaryProfileContract + Projection + Actual
                    ↓
            SummaryContent (semantic, no geometry)
                    ├── SourceInput text runs → measurement → Layout allocation
                    └── final SurfaceContentInput → Layout placement → Scene → renderer
```

## Closed design

### D86-1: SummaryContent is the pre-layout semantic boundary

Introduce frozen `SummaryPanel` and `SummaryTextRun` values.  Each run contains
a stable placement identity, source panel identity, already formatted text, and
its declared typography role.  A panel's title is a `summary` run; a `lines`
metric is one `summary` run; a `figures` metric is, in order, one `metric` value
run and one `summary` caption run.

`normalize_summary_content(profile, projection, actual)` is the only resolver
of summary metric sources and formatting.  It is called once by the render use
case after projection and before measurement.  The final general content
normalizer receives the resolved `SummaryContent`; it does not re-read the
summary YAML or reformat a metric.  An absent profile resolves to an explicit
empty value.  This is a semantic value, not a second authoring resource or an
incomplete `SurfaceContentInput`.

### D86-2: Exact mixed-typography source measurement precedes allocation

`SourceInput` gains ordered text runs, each with its typography role.  Its
legacy one-role lines remain a construction convenience for unaffected sources,
but measurement normalizes both forms to the same run sequence.  Width is the
maximum measured run width; block size is the sum of each run's own
`font-size × line-height`; first-baseline metadata comes from the first run.

The summary slot's input is made directly from `SummaryContent.runs`, replacing
the literal `"summary"` stub.  Therefore `blockSize: content` reserves the
actual authored panel height before sibling `notes` and `legend` slots are
placed.  This refactor is shared measurement infrastructure, not a
summary-specific layout branch.

### D86-3: Layout places the canonical run sequence

The surface composer iterates `SummaryContent.runs` once, advances its cursor by
the current run's own measured line advance, and creates a `TextPlacement` from
that run.  It must not infer a different title/value/caption sequence, use a
summary line height for a metric run, or consult a renderer.  Slot geometry,
overflow, collision validation, and any ellipsis stay Layout responsibilities;
Scene only maps the completed placements to the existing summary semantic
bindings.

This preserves Specification 50's `SurfaceLayoutRequest → SurfacePlacement`
handoff.  There is no new primitive, renderer convention, per-example offset,
or Scene measurement path.

### D86-4: Theme remains paint authority

The HALCYON wallboard profile intentionally asks for `figures`, whose values
use the existing `metric` semantic role.  Its missing `metric.fill` binding is
an authored Theme error, not a reason for the renderer to substitute a colour
or for Layout to choose paint.  The implementation adds the valid role binding
to the wallboard theme in the same atomic change that activates its summary.

## Whole-architecture consistency review

| Authority | Decision | Consistency result |
| --- | --- | --- |
| Closure/schema | Typed profile contract is resolved at ingress; no YAML mapping crosses a new boundary. | Matches #99 schema-first typed contracts. |
| Projection/content | Summary metric selection and formatting are normalized once into an immutable semantic value. | Prevents a second summary parser and honours Specification 09's typed stage values. |
| Measurement/Layout | Exact text runs are measured and arranged before Scene, using pinned font metrics and declared theme typography. | Matches Specification 08 §2.2 and Specification 50 §§1–2. |
| Scene | Projects completed text placements through existing semantic registry entries. | Retains the #58/#99 no-measurement, no-coordinate-search rule. |
| Theme | Supplies role tokens, including `metric.fill`; no fallback colour exists. | Retains Theme's paint ownership. |
| Renderer | Serializes existing text and rect primitives only. | Does not broaden renderer authority or obstruct #122's Renderer seam. |

ADR-0031 rejects Scene-owned collision repair and example-specific geometry;
this design adds neither.  It also preserves the Issue #94 completed-input
decision: only `SummaryContent` is available before layout, while the complete
`SurfaceContentInput` is constructed at its existing final boundary.  The
normalizer is not bypassed and `SurfaceContentInput` is never partially
constructed.

## Delivery plan

1. **C86-1 — semantic content and measurement.** Introduce frozen summary
   values and the shared text-run measurement representation.  Resolve a typed
   bound summary profile once, add it to the read ledger, and feed its exact
   runs into pre-layout source inputs.  Preserve output until placement and
   authoring are adapted in C86-2.
2. **C86-2 — placement and HALCYON acceptance.** Place canonical runs with
   per-run advances; pass the resolved value into final surface content; add
   the wallboard metric role binding; regenerate only affected public evidence.
   Remove all `summary-profile` unused-input pins and the resolved summary-slot
   property pin in the same change.
3. **C86-3 — review gate.** Run focused unit/acceptance tests, full pytest,
   reachability/import checks, all five public materializers, and inspect the
   generated SVG diff.  Confirm the summary profile is consumed in every bound
   context and that no unrelated known-failure fingerprint changes.

Each slice is independently reviewable.  C86-2 may not start until C86-1 is
merged; C86-3 is the acceptance gate for the implementation PR.

## Acceptance criteria

- Every bound `summary-profile` is recorded as read by `render-review`.
- Summary source measurement matches the exact ordered placed run sequence,
  including figure values and captions with distinct typography.
- A content-sized summary slot is allocated from that measured content; no
  summary, note, or title placement overlaps as a result.
- The HALCYON programme-board emits the declared summary primitives with a
  valid `metric` theme role; only intentional generated evidence changes.
- Existing #85 output-property pins remain unchanged except the #86-owned
  summary-slot pin; all five materializers and the full suite pass.

## Authorization

This review authorizes an implementation plan only.  It does not authorize
source, schema, theme, or generated-output changes until that plan is published
and merged.
