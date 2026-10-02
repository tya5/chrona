# Work Record - Show and spell the deadline (#822, successor of #792)

**Status:** Proposed. One concise living record for the AGENTS.md sequence: baseline, design plan, design, architecture
review, implementation plan, progress. It continues the [#792 work record](issue-792-deadline-warning-work-record-2026-10-02.md)
(decisions D9 and D10 there deferred exactly these two surfaces) and its
[acceptance review](../../reviews/current/issue-792-deadline-warning-acceptance-review-2026-10-02.md).
**Public base:** `main` at `339d87d4`. Every PR is `Refs #822` with no closing keyword.

## 1. Published baseline (verified on `main`)

The issue (body, no comments at 2026-10-02) asks for two surfaces `#792` left open: a View concept for a slipped deadline,
and a terse spelling. Neither may change a verdict or a placement.

1. **The fact and the check exist.** `deadline` is an optional date on every Project object (Spec 05 section 9). Since
   `#792`, `core/deadlines.py:deadline_warnings(project, placements)` names each object whose planned finish (`at` of a
   point, `end` of a span or rollup) is strictly after its deadline and returns one `W_DEADLINE` `Diagnostic` (`details`:
   `object`, `endpoint`, `finish`, `deadline`, `daysLate`). It runs after scheduling and never moves a placement
   (Q-SCHED-2). `chrona schedule`, MCP `schedule_project` and `render` stderr carry it; the SVG of a plan with a missed
   deadline is byte-identical to the plan without it.
2. **No presentation reads it.** `ReviewProjection` has no deadline; the Layout, Scene and adapters know no deadline
   semantic, role or vocabulary entry. The skill says "the picture does not draw it yet" (`skills/chrona/SKILL.md`).
3. **How a per-object mark is drawn today.** `layout/surface_marks.py:compose_surface_marks` completes one `MarkPlacement`
   per planned, actual, snapshot or scenario facet (`planned:<instance>`, semantic `planned`), in the row's track frame; lane
   rows go through the same function with a lane owner. Decorations that follow a View declaration use the `#582` shape:
   a View member selects (`periods`), Core resolves dates (`core/periods.py`), the use case attaches typed values to
   `ReviewProjection` (`_selected_periods`), a Layout module completes geometry (`surface_periods.py`), the semantic
   registry names the meaning (`model/semantic_registry.py`), `scene/capabilities.py` closes the Theme role, and the Scene
   builder emits the primitive. A View that selects a period needs the Theme role (`E_THEME_ROLE_REQUIRED`); there is no
   fallback. Bundled presets declare `period-band` since `#880`.
4. **Legends are declared, not inferred.** Legend entries come from the Detail Profile (`legend: [{role, label}]`);
   `layout/surface_legend.py:swatch_extent` draws a line swatch for the roles `asOf`, `dependency` and
   `dependency-critical`, and a mark swatch for the mark roles. A new line role joins that table.
5. **Contrast and perceptibility.** `scene/contrast_policy.py` gates every role classified in the semantic registry:
   `ContrastClass.MARK` requires 3:1 of the paint against the ground under the primitive's bounds centre (Rect and Symbol
   hosts earlier in paint order, else the canvas); `scene/perceptibility.py` reports occlusion and text intersection.
   `tools/presentation_contrast.py` requires a corpus witness only for the `DECORATION` class.
6. **Terse.** Spec 65 `terse 0.1` (grammar section 3.1, mapping section 4, scope rule 1.1). `chrona.terse` imports only
   `chrona.core`. `deadline` is `yaml-only` in `terse/ledger.py` ("a promise checked by W_DEADLINE, not a date"; the same
   sentence is in Spec 65 sections 1.1 and 4, the card `docs/guides/terse-plan.md` ("What the syntax cannot say", 120 lines,
   the cap `tests` pin), and the ledger test's yaml-only list). `tools/check_documented_commands.py` compiles every `chrona`
   fence; `docs/guides/terse-plan-mapping.md` holds executable plan and YAML pairs.

Inferred, to confirm in the design: that one Core function can serve both the warning and the mark so presentation never
recomputes lateness; that Layout can anchor the mark to the completed planned mark without a new track allocation.
Unverified until rendered: how the mark reads next to labels, dependency routes and the as-of rule (every slice is read as
an image).

## 2. Literal acceptance (copied from #822)

1. A slipped deadline has a drawn form (or the design states why it does not), through View, Layout, Scene and the adapters.
2. A terse plan can state a deadline, or the ledger states why it cannot.

Also from the issue body: neither surface changes a verdict or a placement; the View concept is "a View, Layout and Scene
design"; the terse clause is "a new keyword (grammar, source map, normalisation rule, fixtures in Spec 65, owned by the #148
line)".

## 3. Dependencies and neighbours

- `#792` (merged) supplies the rule and `W_DEADLINE`; `#582` and `#586` supply the View-declaration, resolve-in-Core and
  reuse patterns this design follows; `#148` owns Spec 65.
- `#584` (annotation kinds: Theme and annotation files, another agent) is not touched: no change to annotation files,
  `view-v0.28` members it adds are merged by rebase. `#718` (presets), `#813`, `#829`, `#880` are other lanes; this work
  edits no file under `src/chrona/resources/presets/` and no scheduler file.
- `#454` is never edited or commented on.

## 4. Design plan

### Use cases

| Id | Use case | Surface |
| --- | --- | --- |
| U1 | A reviewer sees at a glance which rows promised a date they will miss, and by how far, without reading a warning list | View mark on the chart |
| U2 | A board shows every promise (kept and slipped) so a kept deadline reads as slack | `show: all` |
| U3 | The mark survives greyscale and print: slipped and kept differ by shape, not only by colour | Theme-independent encoding |
| U4 | A legend explains the mark through the existing Detail Profile legend | legend |
| U5 | A terse plan states a deadline on the line of the thing it promises | terse clause |
| U6 | Default output of every existing View, Theme, Layout, Project and terse plan is unchanged | all |
| U7 | A deadline the chart cannot place (outside the window, an object folded into a group header) is recorded, never silently missing | diagnostics |

### Open decisions (closed in section 5)

- **D1 the visual.** What is drawn and where.
- **D2 where it is declared.** View, Theme or Project.
- **D3 which objects.** Only slipped, or all with a deadline.
- **D4 the encoding.** Colour, shape or text for slipped versus kept.
- **D5 who decides "slipped".** Core, Layout or the use case.
- **D6 Theme contract.** Required role versus a fallback; bundled presets.
- **D7 legend.** Automatic or the declared Detail Profile entry.
- **D8 terse spelling.** Keyword status (reserved or contextual), position, which kinds, versioning.
- **D9 failure behaviour.** Outside the window, folded points, dependency-network, missing Theme role.

### Architecture review questions

- Does Core own the lateness rule once (`W_DEADLINE` and the mark cannot disagree), with presentation receiving finished dates?
- Is the Layout geometry computed from completed values (scale, completed planned mark, Theme numbers) with no date arithmetic and no new track allocation?
- Is the mark a registered semantic with a closed Theme role, a contrast class and a delivery path (`check_semantic_registry_reachability`, `check_scene_primitive_delivery`)?
- Does the View addition follow Spec 56 section 3.2 (optional, in place, no bump) and pass `python -m tools.schema_equivalence --base-rev origin/main`?
- Byte identity: a View without `deadlines` and a terse plan without the clause produce exactly today's Scene, SVG and Project for every committed example.
- Does `chrona.terse` still import only `core`, and does the grammar change stay additive (every plan that compiled yesterday compiles to the same Project)?
- Does anything collide with `#584`, `#718`, `#813`, `#829`, `#880`?

### Acceptance evidence planned

Synthetic tests only (no `examples/` input, as `tests/support/synthetic_review.py` provides): each rule below with edge dates
(equal date kept, one day late, point and span, rollup, deadline before the span start, deadline outside the window, finish
beyond the window), both `show` values, lanes and explicit rows, a Theme with and without the role, contrast failing a too-faint
paint and passing a sufficient one, the legend entry, default byte identity. For terse: golden pairs and one negative fixture
per new failure. Mutation checks on every rule, recorded in each PR. Rendered images of the mark (slipped and kept, span and
point, a label next to it, lanes) read in full. The S0 gate result in the schema PR. The literal acceptance review, the
exact-main three-OS run cited on close.

### Order of publication

1. This record (docs PR). 2. I822-1 terse clause. 3. I822-2 Core status refactor. 4. I822-3 the View mark. 5. Acceptance review
and the exact-main run. I822-1 does not depend on I822-2 or I822-3 and may merge first or last.

## 5. Design

### 5.1 The picture (D1, D4)

A deadline is a **tick at the promised date, and a bracket from it to the planned finish when the promise is missed**:

```text
kept (show: all)                       slipped
   |                                      |
 [=====bar=====]    |                 [===|=bar=====]
                    deadline              |______|     <- the run, deadline to planned finish
```

- **The tick** is a vertical line at the deadline date, centred on the object's planned mark, taller than it by the Theme's
  `markReach` (a ratio of the planned mark's block extent, so it reaches above and below the bar).
- **The run** is a horizontal line from the tick's lower end to the planned finish (`at` of a point, `end` of a span; the same
  completed date `W_DEADLINE` compares), drawn only when the finish is after the deadline. It lies below the bar, so it
  never covers the bar's own paint.
- Kept and slipped differ by shape (the run), so a greyscale or print reading holds (U3); the Theme still chooses colour, width
  and dash of the one role.
- No text is drawn: a "N days late" caption is a formatting and locale surface (`#586` owns the figure vocabulary) and is
  recorded as a successor candidate, not an acceptance row. `W_DEADLINE` already states the number.

Rejected: (a) colouring the bar (hides the plan's own state colours and fails greyscale); (b) a period band (a range, not a
date); (c) tick only (cannot show how late); (d) a caption (above).

### 5.2 The declaration (D2, D3)

View `body.deadlines`, optional, in place in `view-v0.28` (Spec 56 section 3.2: behaviour-preserving, no version bump):

```yaml
deadlines:
  show: slipped          # slipped | all
```

- `show` is required inside the member and closed (`additionalProperties: false`). `slipped` draws the mark only for objects
  whose planned finish is after their deadline; `all` draws a tick for every object with a deadline and the run for the slipped
  ones. Absent `deadlines` draws nothing: today's output.
- A `dependency-network` View, which has no timeline, may not declare it (the prohibition list that holds `periods`).
- The View selects; Core decides lateness; the Project owns the date; the Theme owns paint and reach; Layout owns geometry.
  The View never carries geometry or colour.

### 5.3 Who decides "slipped" (D5)

`core/deadlines.py` gains `DeadlineStatus(object_id, deadline, finish, endpoint, days_late)` (`days_late` is the signed
calendar days `finish - deadline`) and `deadline_statuses(project, placements)`. `deadline_warnings` becomes a projection of the
statuses with `days_late > 0` and its output is unchanged (every `#792` test stays as is). The use case
(`render_review._project_review`) selects statuses by `show` into `ReviewProjection.deadlines` (typed `ReviewDeadline`). Layout
receives finished dates and draws; it never subtracts two dates to judge lateness.

### 5.4 Layout, Scene, Theme (D6)

- **Layout.** New `layout/surface_deadlines.py` (one call from `surface_composer.py` after the marks are composed, before the
  obstacle index is built): for each `ReviewDeadline` and each planned mark of that object (`semantic_id` `planned`, not a
  legend swatch, not a folded group-header point) complete a tick `Path` and, when slipped, a run `Path`
  (`deadline:<mark id>`, `deadline-run:<mark id>`, `source_ref` the object id, semantic `deadlineMark`, slot `timeline`).
  Inline coordinates come from the same scale as the marks; the run is clipped to the plot's right edge. Both are registered as
  `rule`-class obstacles so labels and routes avoid them (as the as-of rule is). Lane and explicit rows need no special case:
  the geometry is anchored to the completed planned mark, wherever its track put it.
- **Failure behaviour (D9).** A deadline outside the View window is not drawn and is recorded as the Scene diagnostic
  `I_LAYOUT_DEADLINE_OUTSIDE_WINDOW:<object>`; a planned mark folded into a group header is not decorated and is recorded as
  `I_LAYOUT_DEADLINE_FOLDED:<object>`; neither fails the render. A selected deadline whose object has no planned mark in the
  surface (not selected by the View) is simply absent, as every unselected object is.
- **Registry and Scene.** `model/semantic_registry.py`: `deadlineMark` (`line`, purpose and scene role `deadline-mark`,
  `ContrastClass.MARK`, so the 3:1 gate covers the new ink on whatever it lies: the row ground or, where the tick crosses a bar,
  the bar). `scene/capabilities.py`: role `deadline-mark` with the path paint set plus `markReach` and `markPaintOrder`
  (Scene kind `Path`). `model/theme_tokens.py`: `deadline_mark(role)` returns `(reach, paint order)`, `reach > 0`, an integer
  paint order, and raises `E_THEME_ROLE_REQUIRED` at `/body/roles/deadline-mark` when a View that shows deadlines meets a Theme
  without the role. `scene/v05_builder.py` emits the `Path` primitives; the SVG adapter already serialises Paths. A Theme binds
  colour with `deadline-mark.stroke` and width and dash with the role, like `as-of`.
- **Bundled presets** are not extended here (they belong to the preset lane `#718`); a View that shows deadlines on a bundled
  preset gets the stable error until the preset gains the role or the author's Theme adds it. A successor issue records the
  preset adoption (section 6).

### 5.5 Legend (D7)

No automatic legend. An author adds `{role: deadlineMark, label: "Deadline"}` to the Detail Profile legend, the existing
mechanism; `swatch_extent` lists `deadlineMark` with the line roles, so the swatch is a line in the role's paint.

### 5.6 The terse clause (D8)

```text
object   = NAME [ STRING ] KIND [ schedule ] [ "calendar" CAL ] [ after ] [ "deadline" DATE ] ;
```

- `deadline D` is the last clause of an object line, for every kind (a group's rollup finish is its `end`, as `W_DEADLINE`
  judges it). It maps to `objects.NAME.deadline: 'D'` and the source map entry `/objects/NAME/deadline` (the clause), so a
  Core finding at that pointer is positioned.
- **`deadline` is a contextual keyword, not a reserved word.** Reserving it would make an object named `deadline` a
  new `E_TERSE_NAME_RESERVED`, an incompatible change that Spec 65 S1 reserves for `terse 0.2`. As a contextual keyword it is
  recognised only where an object line may continue after its last clause, and a dependency name is still a name after `after`
  or a comma; so every plan that compiled yesterday compiles to the same Project (strictly additive, version stays 0.1), and the
  only newly accepted lines were errors before.
- New normalisation **N8**: none beyond the clause (the date is emitted verbatim; Core validates it with `as_date`, so a
  non-date that passes the lexical shape is `E_SCHEMA` positioned through the source map). New compiler behaviour reuses
  `E_TERSE_DATE_INVALID` (shape or calendar), `E_TERSE_CLAUSE_DUPLICATE` (a second `deadline`) and `E_TERSE_LINE_INCOMPLETE`
  (no date); no new code.
- Scope rule 1.1 (1) is amended: a construct belongs when it determines identity, hierarchy, dates or dependencies, **or is a
  date the plan states about the thing it names**. The ledger entry `object.deadline` becomes `mapped`
  ("`deadline D` clause"), the card's "cannot say" list drops deadlines, the mapping guide gains an executable pair, and the
  emitter writes `deadline` after `schedule` in the fixed key order.
- A compile does not judge the deadline; `chrona schedule plan.chrona` lists `W_DEADLINE` and `chrona render` draws the mark
  when the View asks for it, through the unchanged draft dispatch.

### 5.7 Intended incompatibilities

None. `deadlines`, the clause and the legend role are additions; omitting them is today's output; the new diagnostics and the
Theme-role error are raised only by a document that uses them.

### 5.8 Specifications

04 section 10 (one sentence: the View may draw the finished lateness), 06 (View `deadlines`, section 7.3), 07 (the Theme role
and its properties), 49 (registry row), 50 (the geometry, the obstacle rule and the failure records), 65 (grammar, mapping,
scope rule, N8, source map). Each is updated by the slice that changes behaviour, never copied into this record.

## 6. Architecture review

- **One lateness rule.** `W_DEADLINE` and the mark both read `deadline_statuses`; Layout never judges. A test pins that the set
  of marks with a run equals the set of `W_DEADLINE` objects.
- **Layering.** Project fact (date) to Core (status) to use case (selection by the View) to Layout (geometry from completed
  values) to Scene (primitive) to adapters (serialise). Import direction unchanged; `chrona.terse` still imports only `core`.
- **Closed by construction.** The `show` enum is closed in the schema; the Theme role is closed in `capabilities.py`; the
  semantic is one registry entry reached by one builder path (the reachability and delivery guards cover it).
- **Contrast.** The role is `MARK`-classified, so a too-faint paint fails the gate; the tick's ground is whatever lies under its
  centre, so a Theme must give 3:1 on the row ground and, where a tick crosses a bar, on the bar. The test fixes both cases.
- **No fallback.** A missing Theme role is an error, as for `period-band`; bundled presets stay with their lane. Reversal of the
  whole feature is deleting the optional member while no committed View uses it.
- **Spec 56.** One optional member added in place to `view-v0.28` plus the prohibition-list entry; the PR runs the S0 gate and
  regenerates the schema inventory.
- **Byte identity.** A View without `deadlines` selects nothing (the use case returns before reading a status) and a terse plan
  without the clause takes no new path, so every committed example regenerates byte-identical (evidence of no change only).
- **Cross-agent files.** Shared and kept minimal: `schemas/view-v0.28.schema.yaml`, `schemas/schema-inventory-v0.1.yaml`, the S0
  baseline, Specifications 04, 06, 07, 49, 50 and 65, `skills/chrona/SKILL.md` (one sentence that becomes stale). No file of
  `#584`, no preset, no scheduler file.
- **Owner-level judgement calls** (options, choice, why and reversal recorded on `#822`): D1 the visual (tick plus run), D2/D3
  View opt-in with `slipped` and `all`, D6 required Theme role with presets deferred, D8 contextual keyword and last position.
- **Successor candidates (not acceptance rows):** a "days late" caption through the `#586` figure vocabulary; preset adoption of
  the `deadline-mark` role (preset lane `#718`); a deadline mark in the dependency network surface; per-object overrides.

## 7. Implementation plan

Each code PR is `Refs #822`, carries the two trailers, is cut from the derived bot commit (`newbranch.sh`), runs the S0 gate when
it touches a schema, regenerates nothing by hand (the derived sync regenerates evidence), keeps every committed example
byte-identical, and states that no `#584`, preset or scheduler file is edited. Every new test is synthetic and mutation-checked,
the result recorded in the PR. Merge procedure: green PR, merge lock, rebase if the base moved, `derived-ready`, merge, release.

### I822-1: the terse `deadline` clause (no schema, no render)

- **Code.** `terse/parser.py` (the clause after `after`; groups too; hints), `terse/compiler.py` (emit and source map),
  `terse/emitter.py` (key order), `terse/ledger.py` (`object.deadline` mapped).
- **Specification and guides.** Spec 65 (sections 1.1, 3.1, 3.2, 4, 6.4, the code lists need no change), `docs/guides/terse-plan.md`
  (stays at or under 120 lines), `docs/guides/terse-plan-mapping.md` (an executable pair), the ledger test list.
- **Tests.** Golden pair with deadlines on a task, a gate, a derived gate and a group; negatives (bad date, impossible date, a
  second clause, no date, `deadline` before `after`); an object named `deadline` compiles as before (additive); source map
  position of a Core finding at `/objects/NAME/deadline`; `chrona schedule plan.chrona` lists `W_DEADLINE`; round-trip and fuzz
  properties still hold; the layering check. Mutation checks: clause ignored, date emitted unquoted, source map entry dropped,
  keyword reserved, duplicate allowed, position not enforced.
- **Gate.** Terse unit tests, `tools/check_documented_commands.py`, conformance, byte identity of every committed example.
- **Boundary.** Merges alone.

### I822-2: Core `deadline_statuses` (no behaviour change)

- **Code.** `core/deadlines.py` (`DeadlineStatus`, `deadline_statuses`; `deadline_warnings` derived from it).
- **Tests.** Every `#792` test unchanged; new unit tests for statuses (kept, equal, late, point, span, rollup, no placement, no
  deadline, order) and the equality with the warning set; mutation: `>` to `>=`, endpoint fallback dropped.
- **Boundary.** Merges alone; no output byte moves.

### I822-3: the View mark

- **Schema.** `schemas/view-v0.28.schema.yaml` (`deadlines`, the prohibition entry), S0 gate with its L1 expected-delta entries,
  `schemas/schema-inventory-v0.1.yaml`.
- **Code.** `presentation/contracts/resources.py` (`ViewInput.deadlines`, parse), `presentation/model/projection.py`
  (`ReviewDeadline`, `ReviewProjection.deadlines`), `usecases/render_review.py` (`_selected_deadlines`), new
  `presentation/layout/surface_deadlines.py` and one call and the obstacle registration in `surface_composer.py`,
  `layout/surface_legend.py` (the line role), `model/semantic_registry.py`, `scene/capabilities.py`, `model/theme_tokens.py`,
  `scene/v05_builder.py`; guards that change with the slice (registry contrast lists, the semantic-reachability and delivery
  tools, the generated-output property test's purpose list) as found by running them.
- **Specifications and skill.** 04, 06, 07, 49, 50; `skills/chrona/SKILL.md` ("the picture does not draw it yet").
- **Tests.** Unit: the contract (shape, closed `show`, dependency-network refusal). Integration through
  `tests/support/synthetic_review.py` with a Theme that declares the role: tick position at the deadline date through the scale;
  run from tick to finish for a span and a point; kept draws no run under `all`; `slipped` draws nothing for a kept deadline; equal
  date is kept; deadline before the bar start; outside the window records the diagnostic and draws nothing; finish beyond the
  window clips the run; explicit and lane rows; a folded header point records `I_LAYOUT_DEADLINE_FOLDED`; labels and routes
  avoid the paths; a missing Theme role is `E_THEME_ROLE_REQUIRED`; contrast passes a sufficient paint and fails a too-faint one
  on the row ground and on a bar; the legend entry draws a line swatch in the role's paint; marks with a run equal the
  `W_DEADLINE` set; a View without `deadlines` has a Scene equal to the base render and an unchanged SVG. Mutation checks on
  every rule (flip the lateness test, drop the run, wrong endpoint, tick off by the half bar, obstacle not registered, filter
  removed, role check removed, selection by `show` inverted).
- **Verification.** Focused tests, conformance, `regenerate_public_examples.py --check` byte-identical, S0 gate, rendered PNGs
  of slipped and kept marks (span, point, lanes, a label beside the mark, a legend) read in full.
- **Boundary.** Merges alone; no committed example changes.

### Acceptance review

After the last merged slice: `docs/reviews/current/issue-822-deadline-mark-and-terse-clause-acceptance-review-<date>.md` with
`<!-- chrona:literal-acceptance/v1 -->`, one row per criterion of section 2 re-fetched from the issue (body and comments),
`tools/check_issue_acceptance_reviews.py` run unpiped, the review merged, the exact-main three-OS run (`workflow_dispatch`)
located on the exact commit that published the review and cited (a later intervening commit is stated, not cited as exact), and
the issue closed only when every row is met or narrowed with a successor link and that run is green.

## 8. Progress and evidence

Nothing implemented yet; this record is the first publication.
