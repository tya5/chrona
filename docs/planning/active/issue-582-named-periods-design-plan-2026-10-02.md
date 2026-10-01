# Design Plan: Named Periods, Labelled and Patternable Bands (#582)

**Status:** Proposed. Design: [issue-582-named-periods-design-2026-10-02.md](../../design/issue-582-named-periods-design-2026-10-02.md). Product code, schemas, examples and derived documents are not changed by this pack.
**Base:** `main` at `4981db0a` (observed 2026-10-02, `derived-main` green).
**Board:** #454 P4-A, first overall; #586 (derived header figures) depends on it; the targets that need it are
listed in #453 and under `docs/research/presentation/*-target-2026-09-26/`.

## Objective

Let an author name a date range, such as a launch window, once in the Project, choose in a View which
named ranges a surface shows and where each label goes, and let a Theme paint the range (fill, stroke,
opacity, an optional catalogue pattern, a label treatment). Layout draws the band beneath the marks and
treats the label as an obstacle. Scene carries both as completed primitives whose `sourceRef` is the
period. No core rule may depend on a project: the design targets (Yuya's seigaiha range, Title Card's
hexagon lattice, Marquee's "Opening night", target B's launch window) are reached afterwards by YAML
only, and are evidence, not a pass condition.

## Verified starting point

Published on `main` and read in the sources named; nothing here was changed.

- **A View's `window` only selects a range.** `view-v0.28` `body.window` has the modes `explicit`,
  `selected-planned` and `selected-comparison`; `[start, end)` is half-open (Spec 06 §7). Nothing names a
  period, so nothing can be drawn for one.
- **The closest mechanisms are the calendar closure and the as-of marker.** `calendarClosed` is a
  `decoration` semantic (`semantic_registry.py`) completed by `compose_calendar_backgrounds` into Rect
  `ShapePlacement`s whose fill, stroke, opacity and paint order come from a Theme role bound by
  `backgroundTreatment` and `backgroundPaintOrder`; Scene emits them as `Rect` primitives with
  `purpose: calendar-closed` (`v05_builder.py`). The as-of marker enters through the View's `markers` and the
  Actual set, and its label is placed by the member-label phase against the shared obstacle index.
- **Catalogue patterns on a Rect are an allow-list.** `axis-band-decoration` shows the full path: a
  `pattern` role binding to a `{kind: catalog}` token, `theme_catalog_pattern_consumer` admitting the role,
  `_RECT_PATTERN_THEME_ROLES` in `surface_completion.py` attaching a completed `PatternedPlacement`, the
  Scene `catalogPattern` shape, and a Scene contrast check over the substrate and the ink
  (`contrast_policy._pattern_findings`). A pattern requires `opacity: 1`.
- **Decoration contrast is gated by a corpus witness.** A `ContrastClass.DECORATION` role is evaluated at
  the 1.10 floor over every committed Scene, and `tools/presentation_contrast.py` fails
  (`E_PRESENTATION_CONTRAST_DECORATION_WITNESS`) when a registered decoration role is painted in no
  committed public Scene. The gate also cannot composite through a translucent host: `_ground_under`
  returns `E_SCENE_CONTRAST_GROUND_UNSUPPORTED` when the Rect under a sample point has `opacity != 1`.
- **Background overlap is policed.** `validate_background_shapes` rejects two intersecting translucent
  fills (`E_LAYOUT_BACKGROUND_OVERLAP`) except a later-painted translucent calendar closure over a row,
  group or header band.
- **Project facts that never schedule have a precedent.** `deadline` (Spec 05 §9) and `attachesTo` (§9.1,
  #486) are in-place optional additions to `project-v0.7`, validated in Core with `E_PROJECT_*` codes, and
  read after scheduling without moving a placement. `Scene` already accepts any `purpose`, `visualRole` and
  `sourceRef` string, so a new primitive family needs no Scene schema change.
- **The Theme role vocabulary is closed by a registry, not by the schema.** `theme-v0.13` `body.roles` is an
  open map; `scene/capabilities.py` states which properties each known role admits and which Scene kinds it
  reaches, and closure rejects a property with no consumer.
- **The corpus has the data for one target.** HALCYON-1 states "Launch window 22 Oct-5 Nov" in a Project
  annotation and has a `launch` gate object ("Launch window opens", 2027-10-22), but no object or field
  carries the window's end, which is why the targets say "no named ranges".

**Inferred, to be confirmed in the slice that touches it:** that a View naming a period requires its Theme to
declare the `period-band` role (a missing role is `E_THEME_ROLE_REQUIRED`, as for `calendarClosed`); that
adding a Project member changes the Project `contentIdentity` pinned by every HALCYON context, so the
corpus evidence slice re-pins them; that the use-case layer, not the scheduler, is where a period that
depends on a derived date is checked.

**Unverified:** whether any packaged preset or part (the #718 lane) will need the new Theme roles; how the
legend lane (#497) will key a legend entry for a period; how the axis lane (#492) will change
`surface_axis.py`. This work reads none of them and edits none of those files.

## Literal acceptance (issue #582, copied)

| # | Literal item | Where addressed |
| --- | --- | --- |
| 1 | Project schema: named periods with validation (ordering, unknown refs) and diagnostics. | Design D1 to D3; slices S1, S2 |
| 2 | View selection and label placement, with Theme paint including an optional catalogue pattern; synthetic tests cover each option. | Design D4 to D6, D8; slices S3, S4 |
| 3 | Scene carries the band and label as completed primitives with the period as sourceRef; contrast and perceptibility gates cover them. | Design D7, D9; slices S3, S4 |
| 4 | Evidence: one corpus slide shows a launch window through YAML only. | Design D10; slice S3 (band), completed by S4 (label) |

Also from the issue body, as constraints: "core gets general declarative knobs only, tested on synthetic
fixtures"; "a period is a project fact, so it belongs in the Project, not in presentation"; "Layout draws the
band beneath the marks and treats the label as an obstacle".

## Use cases the design must serve

1. **Launch window (HALCYON, target B, Marquee, Title Card, Yuya).** One range with two literal dates, a label
   at the top of the plot, a Theme fill and optionally a pattern.
2. **A range tied to the plan.** A freeze that starts when `cdr` ends: a date reference to an object
   endpoint, so a re-plan moves the band (this is why the issue says "date references").
3. **Several ranges.** A freeze, a review week and a launch window on one slide, each selected by the View.
4. **A range without a label** (a quiet wash) and a label that does not fit (a narrow range on a long axis).
5. **A narrower View window.** A range partly or wholly outside the surface window.
6. **A downstream consumer.** #586 will derive "days until the launch window" from the same facts, so the
   resolved range must be a stable Core value, not a Layout internal.

## Open decisions

Each is decided in the [design](../../design/issue-582-named-periods-design-2026-10-02.md); owner-level ones are recorded with options, choice, reason and reversal on #582.

1. Where the fact lives and its shape (Project `periods`, in place, closed object), and the end convention.
2. What a date reference may name and when its ordering is checked.
3. How the View selects, names the label placement, and what a View may not do.
4. How the Theme paints: roles, pattern admission, paint order, translucency.
5. How the label is placed, measured, and treated as an obstacle; the overflow policy.
6. The Scene shape and the gates that cover it, and the slice order that the corpus witness forces.
7. What a period outside the window, or an empty resolved range, does.

## Responsibility boundaries

| Concern | Owner | Not the owner |
| --- | --- | --- |
| The named range, its dates and references, static validation | Project and `core/periods.py` | View, Theme, Layout |
| Resolving a reference to a date, ordering after scheduling | `core/periods.py`, called by the use-case layer after the scheduler returns | `scheduling/` (not touched) |
| Which ranges a surface shows, label placement and overflow intent | View | Project, Theme |
| Fill, stroke, opacity, pattern, label typography and treatment, paint order | Theme (roles `period-band`, `period-label`, `period-label-chip`) | Layout, Scene |
| Band geometry, label geometry, obstacle registration, window clipping | Layout (`surface_periods.py`) | Scene, adapters |
| Completed primitives, `sourceRef`, contrast and perceptibility evidence | Scene and the existing gates | Layout |
| Serialization | adapters | everything above |

## Data and resource model

```text
Project.periods: { <id>: { title?, start: Date | EndpointRef, end: Date | EndpointRef } }   [start, end)
View.periods:    [ { id, label?: { placement: top | bottom | inside, overflow?: suppress | visible-overflow } } ]
Theme roles:     period-band (Rect paint, pattern, background treatment and order)
                 period-label (text), period-label-chip (chip), colour bindings as for any role
Layout:          Rect "period-band:<id>" (timeline slot), Text "period-label:<id>", obstacle "text"
Scene:           Rect purpose period-band / Text purpose period-label, sourceRef = period id
```

## Migration effects

Every addition is optional and behaviour-preserving, so under Spec 56 §3.2 `project-v0.7` and `view-v0.28`
change in place with no version bump; `python -m tools.schema_equivalence --base-rev origin/main` runs in each
schema PR and its output is pasted there. A Project without `periods` and a View without `periods` produce
byte-identical Scenes. The Theme schema does not change (roles are open); the role registry gains entries. No
Scene, Layout Profile or Render Context schema changes. Existing Projects are never rewritten.

## Design review questions

1. Does any slice change an existing document's verdict, diagnostic, Scene byte or SVG byte?
2. Is the period a Project fact only, with no presentation member in it, and no scheduling edge from it?
3. Can a Theme or View reference a period the Project does not declare without a stable, pointed error?
4. Is every drawn pixel owned by one layer (Layout geometry, Theme paint, Scene primitive), with no adapter
   decision?
5. Can a decoration or text role be painted that the contrast and perceptibility gates cannot evaluate, and
   if so is the failure loud?
6. Does the slice order keep each PR mergeable while the corpus witness requires committed evidence for a
   classified decoration?
7. Does it leave the axis, legend and preset lanes free of edits?

## Acceptance evidence for the design pack

- Four published documents (this plan, the design, the architecture review with findings, the
  implementation plan); every relative link resolves; conformance green.
- No product code, schema, example or derived document changed by these four PRs.

## Order of design slices

1. Baseline and plan (this file).
2. Design (D1 to D11).
3. Architecture review (findings, dispositions, owner-level decisions recorded on #582).
4. Implementation plan (slices S1 to S5 with files, tests, proof and publication boundary).
