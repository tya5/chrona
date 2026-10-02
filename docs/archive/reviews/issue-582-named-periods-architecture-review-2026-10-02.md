# Issue #582: Named Periods, Architecture Review

**Decision:** Accept the [design](../../design/issue-582-named-periods-design-2026-10-02.md) **with conditions**. The
ownership split (Project fact, View selection, Theme paint, Layout geometry, Scene primitive) and the
non-scheduling rule stand. Four findings change the plan: a classified decoration forces its corpus evidence
into the first drawing slice (F1), the contrast gate cannot check a band over a translucent host (F2), the
background overlap rule must be widened by one explicit relation (F3), and the terse-syntax ledger forces a
decision with the first schema change (F5).

Reviewed: the [design plan](../planning/issue-582-named-periods-design-plan-2026-10-02.md), the design, Specifications 05, 06, 49, 50 and 56 §3.2, `core/validation.py`,
`core/attachments.py` and `core/deadlines.py` (the precedents), `usecases/project_checks.py` and
`usecases/render_review.py` (the two scheduling call sites), `presentation/layout/surface_composer.py`,
`surface_backgrounds.py`, `surface_completion.py`, `surface_member_labels.py`, `scene/v05_builder.py`,
`scene/capabilities.py`, `scene/contrast_policy.py`, `tools/presentation_contrast.py` and
`terse/ledger.py`, against `main` at `a03640de`. Checked by reading the sources named and by running
conformance on the unmodified tree. Not checked, and recorded as such: any rendered period (nothing draws one
yet), the legibility of a real label over a real pattern, and the wallboard Theme's paint orders beyond what the
evidence slice will show.

## Boundary audit

| Boundary | Decision | Result |
| --- | --- | --- |
| Project to scheduler | `periods` is read nowhere in `scheduling/`; resolution and the post-placement check are use-case code reading placements | Preserved. No scheduler file is touched; the PR diffs name the directory as untouched |
| Project to presentation | Only `resolve_periods` crosses (typed, pure); a View never reads a raw date | Preserved; `check_import_direction` unchanged |
| View to Layout | Closed vocabulary (`id`, `label.placement`, `label.overflow`); no coordinates, colours or patterns | Preserved |
| Theme to Layout and Scene | Existing role mechanics (`backgroundTreatment`, `backgroundPaintOrder`, `pattern`) and the role registry; no Theme schema change | Preserved |
| Layout to Scene | Completed `ShapePlacement` and label placement; the pattern is completed in Layout (`complete_catalog_patterns`) | Preserved |
| Scene and adapters | No Scene schema change (`purpose`, `visualRole`, `sourceRef` are open strings); SVG gains no new element kind | Preserved |
| Default behaviour | A Project and a View without `periods` produce identical Scene and SVG; each slice proves it | Preserved, per slice |
| Lanes owned by others | Axis (`surface_axis.py`), legend (`surface_legend.py`, detail profile) and packaged presets are not edited | Preserved; see F8 for the one shared file |

## Findings

### F1 (high): a classified decoration cannot merge without committed evidence

`periodBand` must be `ContrastClass.DECORATION` for acceptance row 3 (the contrast gate finds a role only
through `contrast_binding`). `tools/presentation_contrast.py` then fails the whole report with
`E_PRESENTATION_CONTRAST_DECORATION_WITNESS` unless the role is painted in a committed public Scene.
*Disposition:* the first slice that registers and draws the band (S3) carries the corpus evidence through YAML
(design D10). The Project fact (S1) and the resolution (S2) have no Scene and merge earlier. Registering the
role unclassified first and flipping it later was rejected: it would leave a drawn role without its gate for a
slice, which is the defect the acceptance row exists to prevent.

### F2 (high): a band over or under a translucent fill cannot be gated

`contrast_policy._ground_under` returns `E_SCENE_CONTRAST_GROUND_UNSUPPORTED` when the Rect beneath a
sample point has `opacity != 1`, and a catalogue pattern already requires `opacity: 1`. A translucent period
band across translucent calendar closures therefore fails one of the two checks. *Disposition:* not worked
around in the gate. The failure is loud (an error finding, never a silent pass); Theme guidance in the design
(D5) names the two working shapes (opaque substrate with a pattern; translucent band over opaque bands only);
the evidence Theme uses one of them; compositing through a translucent host is a separate contrast change,
recorded as a successor, not folded into this mechanism.

### F3 (medium): the background overlap exception names only the calendar closure

`validate_background_shapes` rejects any two intersecting translucent fills except a later-painted calendar
closure over a row, group or header band. A period band over group bands, and a calendar closure over a period
band, both intersect by design. *Disposition:* widen the exception to one explicit relation, "a later-painted
translucent overlay over an earlier background, with a strictly greater paint order", over a closed rank
(row, group and header bands, then the period band, then the calendar closure). Synthetic tests: each allowed
pair, each reversed pair rejected, equal paint order rejected. The rule stays explicit; no pair is allowed by
default.

### F4 (medium): two scheduling call sites, not one

The post-placement ordering check must run where placements first exist: `schedule_project_mapping`
(`chrona schedule`, the MCP tool) and `_project_review` (render). `review_projects` computes placements for
baseline comparison and reports no diagnostics, so it does not need the check. Snapshot and scenario Projects
are scheduled separately in render; the check applies to the primary Project only (periods are not
scenario-aware, D2). *Disposition:* one function, `period_range_diagnostics(project, placements)`, called at
both sites; a test per site; `validate` documented as unable to see it. A mutation test removes the call at each
site.

### F5 (medium): the terse ledger forces a decision with the first schema edit

`terse/ledger.py` classifies every authorable Project property and `test_ledger.py` fails when a property is
added to `project-v0.7` without a decision. *Disposition:* S1 adds `top.periods`, `period.title`,
`period.start`, `period.end` and the reference members as `YAML_ONLY` with the scope-rule reason (Spec 65 §2:
a period references other sections and has two shapes). A terse spelling is a successor, not an acceptance row.

### F6 (medium): the evidence changes every HALCYON context pin

Adding `periods` to `examples/halcyon-1/project.yaml` changes the Project `contentIdentity`, which all sixteen
contexts pin, and the Scene `provenance` of every HALCYON slide. The pictures of the other fifteen slides do not
change. *Disposition:* S3 re-pins the contexts with the repository's materializer tooling (never by hand), the
derived-sync regenerates Scenes and SVGs, and the slice review states that fifteen SVGs are byte-identical and
that their Scene JSON differs only in the Project identity, by inspection of the batch diff. The June baseline
snapshot Project is not edited (it is a historical, content-pinned plan).

### F7 (medium): a bundled-preset user cannot select a period

A View that selects a period needs `period-band` in its Theme (no fallback, D5), and the bundled presets
declare none. *Disposition:* intended and documented: silent fallback would paint a project fact in a role
chosen by the engine. The roles in the bundled presets belong to the presets lane (#718); the successor issue
records it. The error names the role and the pointer, so the remedy is a one-line Theme addition.

### F8 (low): `surface_composer.py` is shared with the other lanes

The composer is edited by the axis and legend work as well. *Disposition:* keep this slice's edits to the
composer to two calls (band composition after the axis shapes, label request in the pre-route label phase) with
all logic in `surface_periods.py`; rebase before each slice and resolve by reading, never by overwriting.

### F9 (low): half-open ends surprise authors

"22 Oct to 5 Nov" is `end: 2027-11-06`. *Disposition:* the same convention as `fixed-span` and the View window;
Specification 05 gets an explicit example and the `E_PROJECT_PERIOD_ORDER` message shows both dates. The label
carries the title only, so no inclusive-end display rule is introduced.

### F10 (low): perceptibility of a very narrow band

A period shorter than a pixel at a coarse scale is a hairline. The perceptibility gate's micro-size observation
applies to the Scene Rect as to any primitive; no minimum width is added to Layout. *Disposition:* a synthetic
test records the finding; the band is still drawn, because omitting it would hide a declared fact.

## Intended incompatibilities

None. `periods` is optional in both schemas and absent from every committed document until S3's evidence. The
one changed behaviour for existing documents is Scene `provenance` identity in the HALCYON slides (F6).

## Owner-level decisions (recorded on #582 with options, choice, reason and reversal)

1. Half-open `[start, end)` over inclusive end (D2).
2. Date references reuse `endpointRef`, resolve against the primary schedule, and an empty or inverted resolved
   range rejects the plan (D2, D3, F4).
3. In place on `project-v0.7` and `view-v0.28`, no version bump (D1, D4).
4. One shared `period-band` role; per-period variants deferred (D5, D11).
5. No Theme fallback and no preset edits in this issue (D5, F7).
6. Classified decoration with evidence in the first drawing slice (F1).
7. A period outside the window is omitted with an `I_LAYOUT_PERIOD_OUTSIDE_WINDOW` Scene diagnostic (D6).

## Verdict

Proceed to the implementation plan with F1 to F5 as slice conditions, and F6 to F10 as slice-review items.
