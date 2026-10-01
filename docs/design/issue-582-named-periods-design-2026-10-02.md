# Design: Named Periods, Labelled and Patternable Bands (#582)

**Plan:** [design plan](../planning/active/issue-582-named-periods-design-plan-2026-10-02.md).
**Status:** Proposed; reviewed in the architecture review that follows this design in the pack.
**Normative homes (updated by the slice that changes behaviour, never copied here):** Specification 05 (Project),
06 (View), 49 (semantic registry), 50 (surface backgrounds and label obstacles).

## D1. The fact: Project `periods`

A Project gains an optional top-level map `periods`, keyed by an author-chosen id:

```yaml
periods:
  launch-window:
    title: Launch window
    start: {object: launch, endpoint: at}    # a date, or an endpoint of a Project object
    end: 2027-11-06                          # exclusive, like every Project span
```

Members: `title` (optional string; the label text, falling back to the id as objects do), `start`, `end`
(required). The object is closed (`additionalProperties: false`). It is added to `project-v0.7` in place with no
version bump (Spec 56 §3.2): an optional property whose omission preserves behaviour. A period is a Project
fact like `deadline` and `attachesTo`: **it never schedules.** It adds no relation, moves no object, and the
scheduler never reads it (`src/chrona/scheduling/` is not touched). No presentation member (placement, paint,
pattern) is allowed in it.

## D2. Date forms and the end convention

`start` and `end` are each an ISO date or an `endpointRef` (`{object, endpoint}`, the existing Project
definition). A date reference resolves to the completed placement the scheduler already produced for that
object endpoint (`start`, `end` or `at`), exactly as a relation endpoint names one. The two sides are
independent, so a window may open at a gate and close on a literal date.

A period is the half-open range `[start, end)`, the convention of every Project span (`fixed-span`, Spec 05
§4.1) and of the View window (Spec 06 §7). "22 Oct to 5 Nov inclusive" is written `end: 2027-11-06`. A
period must satisfy `start < end`; a zero-length range is not a period (use a milestone).
Inclusive-end display is a label or formatting concern, never a Core rule (Spec 06 §7).

*Owner-level choice (recorded on #582):* half-open over inclusive; reversible by a documented schema-level
migration only, so it is chosen for consistency now.

Periods are not scenario-aware and not overridden by a scenario's `objectOverride`; a reference resolves
against the Project's primary schedule, the one the View's primary rows use. A snapshot Project carries its
own `periods` like any other member. Derived dates are therefore as stable as the plan they name.

## D3. Validation and diagnostics

Static (in `validate_project`, Core, no dates computed), pointer `/periods/<id>/...`:

| Code | When | Pointer |
| --- | --- | --- |
| `E_SCHEMA` | member shape, or a date that is not a calendar date (`as_date`, as for `deadline`) | the offending member |
| `E_PROJECT_PERIOD_ORDER` | both sides are literal and `start >= end` | `/periods/<id>` |
| `E_PROJECT_PERIOD_OBJECT_UNKNOWN` | a reference names no Project object | `/periods/<id>/<side>/object` |
| `E_PROJECT_PERIOD_ENDPOINT_UNAVAILABLE` | the endpoint does not exist on the referenced schedule mode (`at` on a span; `start` or `end` on a point), the rule relations already apply | `/periods/<id>/<side>/endpoint` |

After scheduling (use-case layer, `schedule` and render, reading placements the scheduler returned): a
period with at least one reference whose resolved range is empty or inverted is `E_PROJECT_PERIOD_ORDER`
with the same pointer and a message naming both resolved dates. It rejects the plan like any other
post-placement contradiction (exit 1). It is checked whether or not a View selects the period: an invalid
declared fact is invalid regardless of use, the same rule `validate` applies to literals. `validate` cannot
report it (no dates are computed there), the same split that exists for `E_FIXED_TARGET_VIOLATION`.

*Owner-level choice (recorded on #582):* reject, rather than warn (`W_DEADLINE`'s shape). A deadline is a
promise compared with a plan, so lateness is information; a period with no extent is not drawable and cannot
be a fact. Reversal: demote the code to a warning and omit the band, one function in `core/periods.py`.

Resolution lives in `core/periods.py` (`resolve_periods`) as a pure function over `(project, placements)`
returning typed `ResolvedPeriod(period_id, title, start, end)` in Project order. It is the single source for
Layout and for #586's "days until the launch window".

## D4. The selection: View `periods`

`view-v0.28` `body.periods` is an optional array, added in place; its omission selects nothing:

```yaml
periods:
  - id: launch-window
    label: {placement: top, overflow: visible-overflow}
```

* `id` (required): a Project period id. Entries are unique by id (`E_VIEW_PERIOD_DUPLICATE`, a typed View
  contract error like `E_VIEW_TABLE_COLUMN_DUPLICATE`). An id the Project does not declare is
  `E_VIEW_PERIOD_UNKNOWN` at `/body/periods/<i>/id`, with the declared ids in the detail, raised where the View
  meets the Project (render). Nothing is silently skipped.
* `label` (optional): absent draws a band with no label. `placement` is one of `top`, `bottom`, `inside`;
  `overflow` is `suppress` or `visible-overflow`, default `visible-overflow` (an author-declared label does not
  vanish silently; the same default as `visibility.labels`).
* Selection order is the View's order and breaks paint-order ties. The View never carries geometry, colour or
  a pattern.
* `surface: dependency-network` forbids `periods` (it has no timeline), added to the same prohibition list as
  `markers`, `shading` and `axis`.

## D5. The paint: Theme roles

The Theme schema does not change (roles are open maps). The role registry (`scene/capabilities.py`) gains:

| Role | Reaches | Properties |
| --- | --- | --- |
| `period-band` | Layout background and Scene Rect | the patterned-Rect paint set (`fill`, `stroke`, `strokeWidth`, `dash`, `opacity`, gradient and shadow, `pattern`) plus `backgroundTreatment` and `backgroundPaintOrder`, as `axis-band-decoration` |
| `period-label` | Layout text and Scene Text | text measurement set, text paint, `contrastTreatment` |
| `period-label-chip` | Layout label chip and Scene Rect | as the existing chips (`chipPadding`, `markCornerRadius`, patterned Rect paint, `backgroundTreatment`) |

* `period-band` is admitted to the catalogue-pattern allow-list (`theme_catalog_pattern_consumer`,
  `_RECT_PATTERN_THEME_ROLES`), so a seigaiha or hexagon lattice is a Theme `pattern` token. A pattern requires
  `opacity: 1` (existing rule).
* `backgroundTreatment: none` is an explicit non-drawable disposition and yields the existing
  `decorationDispositions` "absent" record automatically.
* Paint order is the Theme's `backgroundPaintOrder`. A Theme places the band above the row and group bands it
  should cover, below calendar closures and below every mark.
* **Translucency.** A translucent band is legal; the contrast gate cannot composite through a translucent host
  (`E_SCENE_CONTRAST_GROUND_UNSUPPORTED`), so a role painted over or under another translucent fill fails
  loudly rather than passing unchecked. Guidance for a Theme: an opaque substrate with a pattern, or a
  translucent band over opaque bands only. Compositing through a translucent host is a separate contrast
  change and is out of scope.
* **A View that selects a period requires the Theme to declare `period-band`** (and `period-label` when a label is
  declared): a missing role is `E_THEME_ROLE_REQUIRED` at `/body/roles/period-band`. There is no fallback to
  another role. Bundled presets are not extended in this issue (the packaged presets/parts lane, #718, owns
  them); a bundled-preset user adds the roles in their own Theme (a derived Theme can inherit one).
* Colours bind through the existing `<role>.fill` and `<role>.stroke` colour bindings.
* One shared `period-band` role paints every selected period. Per-period variants are a successor (D11).

## D6. The band: Layout

`surface_periods.py` completes one `ShapePlacement` per drawable selected period:

* Inline extent from the same time scale that places marks: `[max(start, window.start), min(end,
  window.end))`. Block extent is the timeline slot's plot rows (the extent `calendarClosed` already uses; the
  axis lane is excluded). Placement id `period-band:<period id>`, `source_ref` the period id, `semantic_id`
  `periodBand`, `slot_id` `timeline`, paint order from the Theme.
* A period with no intersection with the window is omitted and recorded as the Scene diagnostic
  `I_LAYOUT_PERIOD_OUTSIDE_WINDOW:<period id>`; it never extends the window and never fails the render. A
  clipped period is drawn clipped. A range that clips to zero width is omitted the same way.
* The band is **not** an obstacle (backgrounds deliberately do not enter the obstacle index); marks and text
  draw over it.
* Overlap policy: `validate_background_shapes` keeps rejecting two intersecting translucent fills, and its
  single exception generalizes from "a later calendar closure over a row, group or header band" to "a
  later-painted translucent overlay (period band, then calendar closure) over an earlier background", each with
  a strictly greater paint order. The relation stays explicit; there is no implicit ordering.
* Draw order in composition: row and group bands, axis shapes, period bands, calendar closures, as-of rule,
  marks. Paint order, not list order, decides the final stack.

## D7. The Scene shape

No Scene schema change. Per period: one `Rect` (`purpose` and `visualRole` `period-band`, `sourceKind`
`decoration`, `sourceRef` the period id, `slotId` `timeline`), optionally a catalogue `pattern`; one `Text`
(`purpose` and `visualRole` `period-label`, `sourceRef` the period id) when a label is declared and placed; one
chip `Rect` (`period-label-chip`) when the Theme binds it. The semantic registry gains `periodBand`
(`decoration`, `ContrastClass.DECORATION`), `periodLabel` (`label`, `ContrastClass.STATE_TEXT`) and
`periodLabelChip`. Every entry must be reachable (`check_semantic_registry_reachability`) and delivered
(`check_scene_primitive_delivery`).

## D8. The label

Text is the period `title` (the id when absent), measured by Layout with the `period-label` typography and
`textTransform`, like every label. Anchors, in the plot (the timeline rows region):

* `top`: block start at the plot's top edge plus the label gap; `bottom`: block end at the plot's bottom edge
  minus the gap; `inside`: centred on the band in both axes. For `top` and `bottom` the inline start is the
  band's visible start, shifted inward so the box stays inside the plot.
* The period label is one more request to the shared label engine that already places the as-of label and member
  labels (`LabelRequest`, `surface_member_labels.py`), with the three anchors above as its candidate list. It
  therefore inherits, rather than re-implements, the obstacle index (marks, text and rules registered so far),
  the collision predicate, the chip, and the suppression and overflow records. The first candidate with no
  collision wins. If none exists, `overflow: suppress` omits the label and records the existing
  `W_LAYOUT_LABEL_SUPPRESSED` fact; `visible-overflow` places it at the preferred anchor and records
  `W_LAYOUT_LABEL_OVERFLOW`. A label never silently overprints a mark. Whether the request is built in
  `surface_member_labels.py` or in a sibling module that hands requests to it is an internal choice recorded
  in the slice.
* **The placed label is an obstacle** (class `text`) for everything placed after it, as every placed label is. The
  period request is built in the first (pre-route) label phase, so relation routes, relation labels, later member
  labels and annotations avoid it. A chip (`period-label-chip`) is a background drawn from the label's measured
  box, through the existing chip mechanism (`label_chip_semantic`), giving the text an opaque ground over a
  pattern.
* The label is a Scene `Text`; its contrast is `STATE_TEXT`, so the Theme states `contrastTreatment`
  (`required` 4.5:1 or `deemphasized` 3.0:1) and the gate evaluates it against the primitive beneath its
  centre (the chip when present).

## D9. Gates and the slice order they force

* `periodBand` is a classified decoration, so the corpus-wide witness requires it to be painted in committed
  public evidence. A classified role cannot be merged without a committed Scene that paints it. Therefore the
  first slice that draws a band also carries the corpus evidence (D10); the Project fact and its resolution
  merge earlier, as they have no Scene.
* Contrast: the band by the 1.10 decoration floor, the label by its declared floor; perceptibility (occlusion,
  text intersection, micro-size) runs over the same Scenes. Synthetic Scene tests exercise both evaluators
  directly (a too-faint band fails, a sufficient one passes).
* Default behaviour: a Project and a View without `periods` produce byte-identical Scene and SVG.

## D10. Evidence

HALCYON-1 (the board target B is drawn from): `project.yaml` gains `periods.launch-window` (`start`
referencing the `launch` gate, `end` the day after 5 Nov 2027), the `wallboard` Theme gains `period-band`
(with a catalogue pattern if one fits) and `period-label`, and `views/02-programme-board.yaml` gains
`periods`. All HALCYON contexts re-pin the Project `contentIdentity`; no source Scene or SVG is hand-edited
(derived-sync regenerates them). The slide is inspected as an image and its Scene read as data before the
slice is accepted. This is evidence against target B, not an oracle; no corpus value is edited to pass a
criterion.

## D11. Not in this design (extension points, successors)

* **Per-period variants**: a Theme role per period or View-chosen variant name (`period-band:<name>`), when a
  slide needs two visibly different ranges.
* **Edge treatments** (dashed or double-ruled edges are available today only as the Rect `stroke` and `dash`).
* **A legend entry** for a period: owned by the legend lane (#497).
* **A date offset in a reference** (`launch + 14d`), **terse-syntax** and **authoring-command** support for
  `periods`, and **bundled-preset** roles (#718).
* **Derived figures** such as days until the window: #586, over `resolve_periods`.
* **Compositing contrast through a translucent host.**

These are not acceptance rows of #582; they are recorded on a successor issue when the design is accepted.
