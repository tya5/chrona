<!-- chrona:literal-acceptance/v1 -->

# Release review — the heading `{calendar}` placeholder prefers a calendar title

Implementation: [#1234](https://github.com/tya5/chrona/pull/1234) (merge `9dd512dd`). A Project calendar may declare an optional `title` (`project-v0.7`, additive in place, Spec 56 3.2); `{calendar}` shows it, else the calendar id. Plan and owner-judgement record: [Status comment](https://github.com/tya5/chrona/issues/1026#issuecomment-6058936223). Target B's adoption of the title in `examples/**` is the reviewer's step and is not a dev row.

## Literal issue acceptance

### Issue #1026

- Source: [Issue #1026](https://github.com/tya5/chrona/issues/1026)
- Observed: 2026-10-08

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | An optional human title on a Project calendar (a Project schema change under Spec 56 3.2) and `{calendar}` preferring it, or a documented decision that the id is the name. | met | [Diff](https://github.com/tya5/chrona/pull/1234/files): `schemas/project-v0.7.schema.yaml` `$defs/calendar/properties/title`; `v05_content._heading_calendar_name`; Spec 05 section 6 and Spec 06 section 7.4; `python -m tools.schema_equivalence --base-rev origin/main` PASS (additive=1). Tests: `tests/integration/test_heading_templates.py` (title present, absent, non-ASCII, SVG escaping, long title) and `tests/unit/chrona/presentation/review/test_v05_content.py`. Mutation check: an id-only helper fails 5 tests. | — |
| 2 | Default output must not change. | met | [PR checks](https://github.com/tya5/chrona/pull/1234/checks) and `tools/regenerate_public_examples.py --check`: PASS, 67 slides byte-identical; no `examples/**` edit; no existing Project declares a calendar title; `test_a_calendar_title_changes_nothing_when_no_placeholder_reads_it`. | — |

## Programme-level criteria (optional)

None.
