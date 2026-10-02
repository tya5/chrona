# Issue #586: derived header figures (work record)

Living record for [#586](https://github.com/tya5/chrona/issues/586): baseline, design plan, design, architecture review, implementation plan and progress. Edited in place; Git keeps history.

**Public base:** `e4429030` on `main`. **Status:** design plan (this revision, sections 1 to 4). Design, architecture review and implementation plan are not yet written; no product code.

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
