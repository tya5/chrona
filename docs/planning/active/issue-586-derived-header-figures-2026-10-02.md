# Issue #586: derived header figures (work record)

Living record for [#586](https://github.com/tya5/chrona/issues/586): baseline, design plan, design, architecture review, implementation plan and progress. Edited in place; Git keeps history.

**Public base:** `f4fd1444` on `main`. **Status:** design plan (PR #900), design and architecture review (PR #904) and implementation plan (PR #908) are published. I586-1 (Core derivation) is implemented in this revision; I586-2 to I586-4 are not yet implemented.

## 1. Published baseline

Issue #586 has no comments (body read 2026-10-02). It is the P4-B item of the header lane; its dependencies #582 (named periods, `core/periods.py`, View `periods`, Theme `period-band`) and #583 (`grouping.header` text template with the closed placeholders `{ordinal}`, `{title}`, `{secondary}`) are merged. #453 lists "no derived summary figure in the header" as a Title Card gap.

Read on `e4429030`:

1. **A summary panel already shows figures, from a fixed set of sources.** The Summary Profile resource (`schemas/summary-profile-v0.2.schema.yaml`, design amendment `docs/specification/46-halcyon-typed-summary-design-amendment.md`) declares panels of typed metrics: `source` is one of `actual.asOf`, `planned.nextPoint`, `count.selected`, `count.missingActual`, `count.knownFinishVariance`, `{actual: asOf}`, `{counts: finishDelta}`, `{scenario: id|title}` or `{object, facet: planned}` (optionally `scope: subtree`); `format` is `text`, `date`, `count` or `signedDays`. `presentation: figures` draws a metric as a display value run (typography role `metric`) over a caption run. The source set is a closed `if/elif` chain in `review/v05_content.py:normalize_summary_content`; a source absent from the Project or Actual Set renders `unknown` with no diagnostic (Spec 46: "absent typed data is rendered as `unknown`"). So **counts by state and the finish delta already exist** as summary sources; **nothing counts days**: no source relates two dates.
2. **The facts a derived figure needs exist as completed Core values.** `core/periods.py:resolve_periods(project, placements)` returns `ResolvedPeriod(period_id, title, start, end)` (half-open, `end` exclusive, a reference resolves to the completed date of an object endpoint, so a re-plan moves it; #582 design plan use case 6 names #586 as its consumer). The as-of is `actual_set.body.asOf` (summary and axis read it there). An object's placed dates are `placements[object][endpoint]` (`at`, `start`, `end`), the same table periods read.
3. **Working-day arithmetic is Core.** `core/temporal.py` has `Calendar` (`is_working`, exceptions), `advance`/`retreat` counting working days strictly after the start, and `as_date`. Project `calendars` and `project.calendar` (the default) declare calendars. No function counts the working days between two dates.
4. **Locale rules the repo already has:** `display_value` / `_format_compact_date` format dates for `en-US` and `ja-JP` and refuse other locales; `count` and `signedDays` (`+3d`) format integers without grouping or numerals; #583 owns the ordinal numeral forms (`group_header_text.py`). No rule formats a bare integer by locale.
5. **A group header text is composed in one pure function.** `presentation/group_header_text.py` parses the template at the contract (closed placeholders, `{{`/`}}` escapes, `E_VIEW_GROUP_HEADER_TEMPLATE`), `review/v05_content.py:_group_headers` composes it, Layout places the finished string.
6. **View is closed.** `view-v0.28` `body` has `additionalProperties: false`; optional properties are added in place (Spec 56 section 3.2, S0 gate, one L1 expected-delta entry each, as #582 and #583 did).
7. **The corpus has the data for the Title Card figure.** HALCYON-1 has `periods.launch-window` (start references `launch`, 2027-10-22; end 2027-11-06), the Actual Set as-of 2027-08-20 and a `key-figures` Summary Profile (`examples/halcyon-1/profiles/summary.yaml`, `presentation: figures`) used by slide 02. The days from the as-of to the window start are 63, the Title Card target's `発射まで 63 DAYS`. This is evidence of the data being sufficient, not a pass condition.

Inferred, to be confirmed in the design: that the declaration belongs in the View (a figure is content the author chooses to show, like `periods` and `grouping.header`) and is consumed by name from the Summary Profile and from header text; that the Core owns every derivation so no presentation module does date arithmetic. Unverified: how the figure text composes with the `metric` typography role in a drawn slide (read as an image in each slice).

## 2. Literal acceptance (copied from the issue)

1. A finite, typed set of figure kinds in the View, with a working/calendar-day option. Synthetic tests cover each kind and edge dates.
2. A figure that refers to a missing period or object gives a diagnostic, not a silent blank.
3. Evidence: the Title Card countdown through YAML.

Also from the issue body, as constraints: "core gets general declarative knobs only, tested on synthetic fixtures"; the design targets "are reached afterwards by preset/Theme/View YAML, which serves as evidence, not as a core pass condition"; "each kind has a declared format and caption, and the calendar semantics (working days or calendar days) are declared"; depth B.

## 3. Dependencies and neighbours

- #582 (merged) supplies `resolve_periods` and View `periods`; #583 (merged) supplies the header template grammar this work extends by one placeholder family.
- The Summary Profile (Spec 46) is the existing figure consumer; this work adds one source to it and leaves its other sources, formats and the `unknown` rule for existing sources unchanged.
- #453 is the reviewer's target gap map (read only; never edited from here). #718 packages targets as presets and parts, #813 (MCP mutating tools), #829 (diagnostic detail) and #880 (presets, axis, period band YAML) are other agents' lanes: this work edits none of their files and keeps shared-file edits minimal (schema inventory, S0 baseline, the specifications named in the design).
- #454 is never edited or commented on.

## 4. Design plan

### Use cases

| Id | Use case | Targets |
| --- | --- | --- |
| U1 | A header figure `63` captioned `DAYS`: calendar days from the as-of to the start of a named period | Title Card (`発射まで 63 DAYS`), target B launch countdown |
| U2 | Working days to a milestone: `15 working days to TVAC exit`, from the as-of to an object's placed date, in a declared Project calendar | any programme board |
| U3 | The length of a named period (`15 days`, `11 working days`) | Marquee, Yuya launch window captions |
| U4 | A figure inside a group header or a label: `ACT II · BUS · 63 DAYS` | Title Card, Sunday |
| U5 | A declared figure whose fact is missing (an undeclared period, an unknown object, no as-of) is a diagnostic, never a blank or a made-up number | all |
| U6 | The default render of every existing View, Theme, Layout and Summary Profile is unchanged | all |

### Slices, ordered by risk

1. **I586-1, the Core derivation.** A pure module `core/figures.py`: the closed fact set, the closed derivation kinds, calendar and working-day counting, and the diagnostics for a missing fact. No schema, no wiring; mergeable alone.
2. **I586-2, View `figures` and the Summary Profile consumer (U1, U2, U3, U5).** The View declaration, its contract validation, resolution in the use-case layer before content normalisation, and the Summary Profile source `{figure: <id>}`. This is the Title Card path.
3. **I586-3, header text placeholder (U4).** A closed placeholder family in the #583 template, validated against the View's declared figures.
4. **Evidence row.** The Title Card countdown through YAML on the HALCYON-1 slide that already shows the key-figure panel is decided in the acceptance review: a YAML-only edit of a Summary Profile and View declaration is evidence, never a core condition and never an edit of corpus data to pass a render criterion; if it is narrowed, the preset catalogue lane (#718) is the successor.

### Open decisions (closed in the design)

- **D1 where the declaration lives.** View `figures` (named, reusable by the summary and by header text) versus extending the Summary Profile source only. Leaning View: header text cannot reach a separate Summary Profile resource without a cross-resource reference, and the same figure should not be declared twice.
- **D2 the fact set.** Which facts a derivation may read; how a period side, an object endpoint and the as-of are named; whether `end` of a period is its exclusive end.
- **D3 the derivation set and its conventions.** Which kinds ship now (counts by state and the finish delta already exist as summary sources); the sign of a past target; the working-day counting convention and its consistency with `advance`; the calendar a working-day figure uses.
- **D4 missing facts.** Error versus warning with `unknown`; which conditions are static (contract) and which need the schedule.
- **D5 formatting.** Which formats a figure value takes in the summary (existing `count`, `signedDays`) and in header text; what the repo's locale rules cover for a bare integer; where the caption lives.
- **D6 the header placeholder grammar.** Whether `{figure:<id>}` fits the closed #583 grammar without a format spec; interaction with `first`, `{{`/`}}` and the secondary pairing rule.
- **D7 layering.** Where facts are gathered and where arithmetic happens, so no presentation module computes a date difference.

### Responsibility and architecture review questions

- Does Core own every derivation, with the use-case layer only gathering facts (as-of, placements, periods, calendars) and passing them in, and Layout, Scene and adapters seeing only a finished string?
- Is the derivation set closed by the schema and by one registry, with no expression, no operator, no free field reference, and a stable error for anything outside it?
- Does a missing or unknown fact always raise a stable diagnostic naming the figure, the fact and the declared alternatives, and is "missing" defined for each fact?
- Is the working-day count the exact inverse of the scheduler's `advance` convention, so the scheduler and a figure never disagree on what a working day is?
- Does the View addition follow Spec 56 section 3.2 (optional, in place, no version bump) and pass `python -m tools.schema_equivalence --base-rev origin/main`; does the Summary Profile addition follow the same rule?
- Byte identity: a View without `figures` and a Summary Profile without the new source render exactly as today, for every committed example.
- Does anything collide with #813, #829, #880 or #718 files?

### Acceptance evidence planned

Synthetic tests only, no `examples/` input: each kind, calendar and working-day counting at the edge dates (same day, adjacent days, across a weekend, across a declared exception, a past target, a target on a non-working day, a period of one day), each fact (as-of, a period side, an object endpoint of a point, a span and a rollup), each missing-fact condition with its code, the placeholder composition, and default byte identity. Mutation checks on every rule. The S0 gate result in every schema PR. Rendered images of the summary figure and of a header placeholder read in full. The literal acceptance review per section 2, with the exact-main three-OS run cited on close.

### Order of publication

1. This plan (docs PR). 2. Design and architecture review, with the Specification amendments planned and the owner-decision comment on #586. 3. Implementation plan. 4. I586-1, I586-2, I586-3 as separate code PRs. 5. Acceptance review and the exact-main three-OS run.

## 5. Design

### 5.1 The declaration

**Where (D1).** View `body.figures`, an optional array, in place in `view-v0.28` (Spec 56 section 3.2: behaviour-preserving, no version bump; omission is today's output). A figure is content the author chooses to show, as `periods` and `grouping.header` are; it is declared once and consumed by name. Each item has an `id` (unique, `E_VIEW_FIGURE_DUPLICATE`; it may not contain `{`, `}` or whitespace, so a header placeholder can name it, a rule the contract checks as `E_VIEW_FIGURE_INVALID`) and a `kind` that selects a closed shape; `additionalProperties: false` everywhere, no expression, operator or free field reference anywhere.

```yaml
figures:
  - id: launch-countdown
    kind: daysUntil
    from: asOf                                   # optional; asOf is the default
    to: {period: launch-window, side: start}
    days: calendar                               # calendar (default) | working
  - id: tvac-working-days
    kind: daysUntil
    to: {object: tvac, endpoint: end}
    days: working
    calendar: engineering                        # working only; default is project.calendar
  - id: window-length
    kind: daysIn
    period: launch-window
    days: working
```

**Facts (D2).** A fact is exactly one of three forms, each a Core value that already exists:

| Form | Value | Source |
| --- | --- | --- |
| `asOf` | the Actual Set as-of date | `actual_set.body.asOf` |
| `{period: <id>, side: start \| end}` | a named period's boundary; `end` is the exclusive end of the half-open range (Spec 05 Periods) | `core/periods.py:resolve_periods` |
| `{object: <id>, endpoint: at \| start \| end}` | an object's placed (completed) date | scheduler placements, as a period reference resolves |

**Kinds (D3).** Two kinds ship; the set is closed by the schema's `oneOf` and by one Core registry, and a new kind is an in-place schema addition plus one registry entry.

| Kind | Value (a signed integer) | Convention |
| --- | --- | --- |
| `daysUntil {from?, to, days, calendar?}` | days from `from` to `to` | Calendar: `to - from`, so a past target is negative and the same day is 0. Working: the count of working days `d` with `from < d <= to`, negated (the days in `(to, from]`) when `to` is before `from`. This is the scheduler's `advance` convention (a working-day `advance` counts days strictly after its start), so `daysUntil(d, advance(d, k wd))` is `k`: the scheduler and a figure never disagree on what a working day is. |
| `daysIn {period, days, calendar?}` | the days a period covers | Calendar: `end - start`. Working: the working days `d` with `start <= d < end`, so the day the period starts is counted and its exclusive end is not. A period with no working day is 0, a value, not an error. |

The two conventions differ because the questions differ (steps from a date, days covered by a range) and each is the natural one for its question; the specification states both with a worked example. No clamping, rounding or absolute value is applied: a past target is a negative number, and the consumer's format decides how it reads.

**Calendar (D3).** `days: working` counts with a Project calendar: the declared `calendar` id, otherwise the Project default `project.calendar`. `days: calendar` never reads a calendar, so `calendar` with `days: calendar` is a dead declaration and `E_VIEW_FIGURE_INVALID`. Counts by state and the critical-path finish delta already exist as Summary Profile sources (baseline item 1) and are not duplicated; the registry is where they could join later, and that is recorded as a successor candidate, not an acceptance row.

### 5.2 Missing facts (D4)

Every declared figure is resolved after scheduling, before content normalisation, in one place. Any condition below is a stable diagnostic that names the figure, the fact and the declared alternatives; the render is refused with all of them (`RenderRejected`, the post-placement precedent of `period_range_diagnostics`). Nothing becomes `unknown`, zero or blank. A figure no consumer uses is still resolved: declaring one asserts the View needs it, and a View used with a Context that lacks a fact should declare another View.

| Condition | Code | Raised at |
| --- | --- | --- |
| Duplicate id; `calendar` with `days: calendar`; `from` or `to` mis-shaped beyond the schema | `E_VIEW_FIGURE_DUPLICATE`, `E_VIEW_FIGURE_INVALID` | View contract |
| A period fact or `period` the Project does not declare | `E_FIGURE_PERIOD_UNKNOWN` (declared ids listed) | resolution |
| An object fact the Project does not declare | `E_FIGURE_OBJECT_UNKNOWN` | resolution |
| An endpoint the object's schedule does not offer (`start` of a point) | `E_FIGURE_ENDPOINT_UNAVAILABLE` (offered endpoints listed) | resolution |
| `asOf` with no Actual Set as-of | `E_FIGURE_ASOF_MISSING` | resolution |
| `days: working` with no resolvable calendar (an id not in `calendars`, or none declared and no default) | `E_FIGURE_CALENDAR_UNAVAILABLE` | resolution |
| A consumer names a figure the View does not declare | `E_VIEW_FIGURE_UNKNOWN` (declared ids listed) | consumer site |

### 5.3 Consumers and formatting (D5, D6)

**Summary Profile (I586-2).** A typed metric `source: {figure: <id>}` takes the figure's integer as its value. The metric's existing `format` applies: `count` is the integer, `signedDays` is `+63d`, `text` is the integer as text; `date` is meaningless for an integer and is `E_PRESENTATION_SUMMARY_FORMAT`. The metric `label` is the caption, so a `presentation: figures` panel draws the value run over the caption run exactly as it draws every other figure, and Title Card's `発射まで ... DAYS` is `label: DAYS` plus a literal. The other sources, formats and the `unknown` rule for them are unchanged. Spec 46 already says absent typed data renders `unknown`; that rule stays for the existing sources, and a figure never reaches it because a missing fact refuses the render first.

**Header text (I586-3).** The #583 closed grammar gains one placeholder family, `{figure:<id>}`, still no expression and no format spec. It renders the signed integer in ASCII digits (`63`, `-3`). The contract checks every `{figure:<id>}` of `text` and `first` against the View's declared figures (`E_VIEW_GROUP_HEADER_TEMPLATE`, declared ids listed); a placeholder with no declared figures is the same error. It composes with `{ordinal}`, `{title}`, `{secondary}`, `first` and `{{`/`}}` unchanged, and the figure value is the same in every group's header (group-relative facts, such as the days to a group's first start, would be a fact-set extension and are a successor candidate).

**Locale and calendar rules (D5).** The repo has no locale rule for a bare integer: `count` and `signedDays` print ASCII digits without grouping, and dates use the `en-US` and `ja-JP` forms. A figure introduces no new locale behaviour; the unit word (`DAYS`, `日`) is author text in the caption or the template, and numerals other than ASCII are #583's ordinal forms only. Calendar rules are the Project's: working days are the Project calendar's `is_working`, including its exceptions.

### 5.4 Layering and ownership (D7)

| Layer | Responsibility |
| --- | --- |
| Core (`core/figures.py`) | The fact and kind registry, the two derivations, calendar and working-day counting, the missing-fact diagnostics. Pure: takes the as-of, the placements, the resolved periods and the calendars as arguments; reads no resource and imports no presentation module. |
| View contract (`presentation/contracts/resources.py`) | Parse `figures` into typed values, duplicate and dead-declaration checks, header-placeholder validation against the declared ids. |
| Use case (`usecases/render_review.py`) | The one place that gathers the facts (as-of from the Actual Set, placements, `resolve_periods`, Project calendars) and calls Core; refuses the render on diagnostics. |
| Content (`review/v05_content.py`) | Substitutes the resolved integers: the Summary Profile source and the header composition. It does no date arithmetic. |
| Layout, Scene, adapters | Unchanged: they place and project finished strings. |

### 5.5 Intended incompatibilities

None. `figures`, the Summary Profile source `{figure: id}` and the `{figure:<id>}` placeholder are optional additions in place; omitting them is today's output; the new codes are raised only by a document that uses the new property.

### 5.6 Spec 56 and the specifications

`view-v0.28` and `summary-profile-v0.2` change in place (section 3.2), each PR runs `python -m tools.schema_equivalence --base-rev origin/main` and records the result, with one L1 expected-delta entry each if the gate asks, and regenerates `schemas/schema-inventory-v0.1.yaml`. Normative text: Specification 05 (a "Derived figures" section: facts, the two derivations with the working-day convention and a worked example, the diagnostics), Specification 06 (View `figures`), Specification 46 (the new source, one paragraph) and Specification 50 section 3.4 (the header placeholder).

## 6. Architecture review

- **No second arithmetic.** All date counting is one Core module reusing `Calendar.is_working`; the working-day convention is stated against `advance` and proven by a test that round-trips `advance`. Presentation gathers facts and substitutes integers.
- **Closed by construction.** The schema's `oneOf` closes kinds and facts; the registry closes the Core side; a hand-written Summary Profile or template cannot name a fact or operator outside it, and every consumer reference is validated against declared ids.
- **Loud, not blank.** Every missing fact refuses the render with a coded diagnostic that lists the alternatives; the Spec 46 `unknown` rule is untouched for existing sources and unreachable for figures.
- **One declaration, several consumers.** Declaring in the View avoids a cross-resource reference from header text to the Summary Profile and avoids declaring a figure twice; the Summary Profile stays the owner of metric id, label, format and order (Spec 46).
- **Spec 56.** Optional in-place additions to two live schemas; the PRs run the S0 gate and regenerate the inventory.
- **Byte identity.** A View without `figures` and a Summary Profile without the source take no new path (the use case resolves nothing for an empty tuple), so every committed example regenerates byte-identical: evidence of no change only.
- **Cross-agent files.** No edit to `src/chrona/scheduling/`, the MCP tools (#813), diagnostic detail (#829), presets, axis or the period-band YAML lane (#880), or `src/chrona/resources/presets/`. Shared files: `schemas/view-v0.28.schema.yaml`, `schemas/summary-profile-v0.2.schema.yaml`, `schemas/schema-inventory-v0.1.yaml`, the S0 baseline, Specifications 05, 06, 46 and 50 (a section or paragraph each).
- **Rejected options.** (a) A `source` kind only in the Summary Profile: header text could not reach it and a figure would be declared twice. (b) A free formula or `{expr}` placeholder: an expression language outside the core. (c) A warning with `unknown` for a missing fact: the issue asks for a diagnostic and a blank-looking figure is the failure it names; reversible by changing the severity in one place if a Context-optional figure is ever wanted. (d) A `daysUntil`-only set: `daysIn` is a different convention that a single kind cannot express. (e) Counting a period's end as inclusive: contradicts the Project convention (Spec 05 Periods). (f) Clamping a past target to 0: hides that the date has passed. (g) Lazy resolution of only the figures a consumer names: typos in unused figures would go undetected and the resolution site would depend on the consumers.
- **Owner-level judgement calls** (options, choice, why and reversal recorded on #586): D1 View declaration versus Summary Profile source, D3 the two-kind set and the working-day convention, D4 eager resolution with an error versus a lazy warning, D6 the header placeholder family.

## 7. Implementation plan

Each code PR is `Refs #586`, carries the two trailers, is cut from the derived bot commit (`newbranch.sh`), runs the S0 gate when it touches a schema and pastes the result, regenerates nothing by hand (the derived sync regenerates evidence), and leaves every committed example byte-identical except I586-4. Every new test is synthetic (no `examples/` input) and mutation-checked. `src/chrona/scheduling/`, the MCP tools, presets and the other agents' files are not edited; the PR says so. Merge procedure: merge lock, rebase on `origin/main`, all checks including `derived-ready`, merge, release.

### I586-1: the Core derivation (no wiring)

- **Core.** New `src/chrona/core/figures.py`: `FigureSpec` (id, kind, `from`, `to`, `period`, `days`, `calendar`) and the three fact forms (as-of, period side, object endpoint); `resolve_figures(specs, *, as_of, placements, periods, calendars, default_calendar)` returning the values in declaration order or the diagnostics of section 5.2 (`E_FIGURE_*`, all of them, with the declared alternatives); `days_until` and `days_in` as the two derivations; `working_days_after(from, to, calendar)` for the shared counting.
- **Specification.** 05: new section "Derived figures" (facts, the two derivations, the working-day convention with a worked example across a weekend and an exception, the diagnostics); `docs/specification/supplemental/core-v0.1-diagnostics.md`: the codes.
- **Tests.** `tests/unit/chrona/core/test_figures.py`: calendar days (same day, adjacent, a past target is negative, month and year boundary, leap day); working days (across a weekend, across a declared working exception and a declared holiday, `to` on a non-working day, a past target, `from` on a non-working day); the `advance` round trip (`daysUntil(d, advance(d, k wd)) == k` over a range of `d` and `k`); `daysIn` calendar and working (a one-day period, a period with no working day is 0, the exclusive end is not counted); each fact (as-of, period start and end, point `at`, span `start` and `end`, a rollup) and each missing-fact code with its alternatives; several figures report all diagnostics. Mutation checks: `<` for `<=` in the working count, end counted, sign dropped, exceptions ignored, default calendar ignored, each diagnostic removed.
- **Staging.** `tools/staged_modules.txt` lists `chrona.core.figures` with the reason that I586-2 wires it (the module-reachability check fails an unreachable module otherwise); I586-2 removes the entry.
- **Gate.** Unit tests for `core`, conformance (the diagnostic inventory is regenerated by the derived sync, not by hand), the import-boundary guards (Core imports no presentation module).
- **Boundary.** Merges alone: no schema, View, Summary Profile, content or Scene change; no byte changes.

### I586-2: View `figures` and the Summary Profile source

- **Schema.** `schemas/view-v0.28.schema.yaml`: optional `figures` (a closed `oneOf` by `kind`; ids keep the sibling `id` form the id-site guard counts); `schemas/summary-profile-v0.2.schema.yaml`: the `{figure: <id>}` source alternative. Both in place, S0 gate, L1 expected-delta entries if asked, `schemas/schema-inventory-v0.1.yaml` regenerated.
- **Contract.** `contracts/resources.py`: `ViewFigure`, `ViewInput.figures` (trailing default `()`), `E_VIEW_FIGURE_DUPLICATE`, `E_VIEW_FIGURE_INVALID`; the Summary Profile source parse.
- **Use case.** `usecases/render_review.py`: gather the as-of, the placements, `resolve_periods` and the Project calendars; call `resolve_figures`; refuse with `RenderRejected` on diagnostics; pass the values to content.
- **Content.** `review/v05_content.py:normalize_summary_content`: the `figure` source (`E_VIEW_FIGURE_UNKNOWN`, `E_PRESENTATION_SUMMARY_FORMAT` for `date`); no date arithmetic.
- **Specifications.** 06 (View `figures`), 46 (the source).
- **Tests.** Unit: the contract (each rejection, the default). Integration through `tests/support/synthetic_review.py`: the countdown in a `figures` panel (value and caption runs; `count`, `signedDays`, `text`), a working-day figure with a Project calendar, a past target, every missing-fact refusal end to end with its code, an unknown consumer reference, a View without `figures` equal to the base render. Mutation checks: facts not passed, values mapped to the wrong id, format `date` accepted, diagnostics swallowed, eager resolution made lazy.
- **Verification.** Focused tests, conformance, `regenerate_public_examples.py --check` byte-identical, one synthetic slide rendered to an image and read in full.
- **Boundary.** Merged alone; the header consumer depends on it only for the declaration.

### I586-3: the header placeholder

- **Grammar and contract.** `presentation/group_header_text.py`: `{figure:<id>}` parsed as a field (the `figure:` prefix and a non-empty id); `contracts/resources.py:_group_header` validates the ids against `figures` (`E_VIEW_GROUP_HEADER_TEMPLATE`). No schema change.
- **Content.** `review/v05_content.py:_group_headers` substitutes the resolved integer (ASCII digits, signed).
- **Specification.** 50 section 3.4: the placeholder.
- **Tests.** Unit: the parser (the placeholder, an empty id, an unterminated one, escapes); contract (unknown id, no `figures`); integration: a header `ACT {ordinal} · {title} · {figure:launch-countdown} DAYS`, with `first`, a negative value, a View without the placeholder unchanged. Mutation checks: id looked up in the wrong table, sign dropped, validation removed. A rendered image read in full.
- **Boundary.** Merged alone.

### I586-4: evidence (the only slice that changes a committed example)

- **YAML only.** `examples/halcyon-1/views/02-programme-board.yaml` declares `figures: [{id: launch-countdown, kind: daysUntil, to: {period: launch-window, side: start}}]`; `examples/halcyon-1/profiles/summary.yaml` gains a metric `{id: countdown, source: {figure: launch-countdown}, label: days to launch, format: count}` in the `key-figures` panel; the context pins are re-pinned by the materializer tool; the README sentence. No Core, schema or Theme change, and no value edited to reach a number: the figure reads the facts the Project already declares (63 days is what they give).
- **Verification.** Rendered PNG of slide 02 read in full; the batch diff shows only the slides that use the edited resources changed.
- **Boundary.** Merged alone. The full Title Card composition (compressed type, hazard tab, canvas lattice) is the preset lane (#718, #882, #585, #587), recorded on the acceptance row as outside this issue.

### Acceptance review

After the last merged slice: `docs/reviews/current/issue-586-derived-header-figures-acceptance-review-<date>.md` with `<!-- chrona:literal-acceptance/v1 -->`, a row per criterion of section 2 re-fetched from the issue (body and comments), `tools/check_issue_acceptance_reviews.py` run unpiped, the review merged, the exact-main three-OS run (workflow_dispatch) located on the review commit and cited, and the issue closed only when every row is met or narrowed with a successor link and the matrix and `reproduction-newest-python` are green on that commit.

## 8. Progress and evidence

### I586-1 (implemented)

- **Behaviour change: none.** `src/chrona/core/figures.py` is new and called by nothing yet (`tools/staged_modules.txt` lists it until I586-2 wires it); no schema, View, Summary Profile, content or Scene change, so no Scene or SVG byte can move.
- **Where.** `core/figures.py` (`FigureSpec`, the three fact forms, `resolve_figures`, `calendar_days_until`, `working_days_until`, `working_days_in`); Specification 05 section 12.2 carries the facts, the two derivations, the working-day convention and its worked example, and the five `E_FIGURE_*` codes (the diagnostic inventory is regenerated by the derived sync).
- **Tests.** `tests/unit/chrona/core/test_figures.py` (47, synthetic): calendar days at the edges (same day, adjacent, past target, month, year and leap-day boundaries); working days across a weekend, a declared holiday and a declared working Saturday, a target and an origin on a non-working day, a past target; the `advance` round trip over 21 origins and 16 counts for two calendars; antisymmetry; `daysIn` (one-day period, a weekend with no working day is 0, exclusive end); each fact form; each missing-fact code with its pointer and alternatives; every finding reported and only the failed figures lose their value; a working figure with no calendar never falls back to calendar days.
- **Mutation checks (all 17 killed).** Target excluded from or origin included in the working count; past target not negated; sign dropped; period end inclusive (calendar and working); exceptions ignored; default calendar ignored; period side swapped; each of the five diagnostics removed; stop at the first finding; values kept when a finding exists (found by this check: the first test set did not cover a working `daysUntil` with no calendar, which would have silently returned calendar days); explicit origin ignored.
