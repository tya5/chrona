<!-- chrona:literal-acceptance/v1 -->

# Literal acceptance review: #1865 rows 1 to 3

Observed on `main` at `b91f0f53c` (the derived-sync bot commit after [PR #1896](https://github.com/tya5/chrona/pull/1896)). [Issue #1865](https://github.com/tya5/chrona/issues/1865) has three numbered rows (rows 1 and 2 carry an `Acceptance:` line; row 3 states "Expect 0 public SVG changes in en-US"). The body and its one comment (the Step 0 finding of 2026-10-21) were re-fetched with `gh issue view 1865 -R tya5/chrona --json body,comments` on 2026-10-22 and counted literally: three rows, no row added since the first reading. Row 1 landed in [PR #1872](https://github.com/tya5/chrona/pull/1872) (`ecc2012ca`), row 2 in [PR #1873](https://github.com/tya5/chrona/pull/1873) (`b796ac2a5`), and the part of row 3 that the reviewer has edited so far in [PR #1876](https://github.com/tya5/chrona/pull/1876) (`423e57ca8`, the reviewer's preset YAML). The issue stays open: row 3 is narrowed, because the Theme annotation kind labels of the approved designs have not adopted the new keys.

## Method

Private venv `/private/tmp/claude-501/venv1682`, `PYTHONPATH=<worktree>/src:<worktree>`, worktree on `origin/main` `b91f0f53c`, no shared install. Every log starts with the command it records. Focused tests: [pytest-1865.txt](assets-1865/pytest-1865.txt) (36 passed; the full suite was not run). The bundled-preset check renders the skill's [notes-and-lanes plan](../../../skills/chrona/examples/notes-and-lanes/plan.yaml) with `target-b` under both locales ([log](assets-1865/row1-3-render-locales.txt)).

## Literal issue acceptance

### Issue #1865

- Source: [Issue #1865](https://github.com/tya5/chrona/issues/1865)
- Observed: 2026-10-22

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | `grouping.missing` (and the role-grouping fallback label) accepts `{wording: key}`. Add wording keys for the defaults the bundled presets use (en-US and ja-JP). Acceptance: a synthetic View grouping by a field with an unassigned row renders the ja-JP wording under `--locale ja-JP` and the en-US wording otherwise; a plain string still works unchanged. | met | The slot accepts `{wording: grouping.unassigned}`; the key exists in both tables of [`wording-tables-v0.1.yaml`](../../../src/chrona/resources/wording-tables-v0.1.yaml) (`Unassigned` and `未割り当て`); the schema [`view-v0.28`](../../../schemas/view-v0.28.schema.yaml) takes the reference. The role-grouping path carries the one `missing` slot unchanged (the Step 0 comment), so it needs no second slot. [`test_grouping_missing_wording.py`](../../../tests/integration/test_grouping_missing_wording.py) renders the synthetic View both as `by: field` and as field-role grouping: ja-JP draws 未割り当て and no English, en-US draws Unassigned, a plain string `Unset` is drawn unchanged in both locales, an unknown key is refused as `E_VIEW_SCHEMA` at `/body/grouping/missing` ([pytest log](assets-1865/pytest-1865.txt)). On a bundled preset: `target-b` draws `Unassigned` under en-US and `未割り当て` under ja-JP ([log](assets-1865/row1-3-render-locales.txt), [en-US](assets-1865/notes-en-US.svg), [ja-JP](assets-1865/notes-ja-JP.svg)). Text in [Spec 06](../../specification/06-view-model.md), [Spec 63](../../specification/63-axis-name-tables.md) and [`locale-and-wording.md`](../../guides/locale-and-wording.md). | — |
| 2 | Theme annotation kind `label` / `secondary` accept `{wording: key}` inside the existing #584 template grammar (or as the whole value). Add keys for note and risk. Acceptance: a synthetic note and risk render localized kind headers in ja-JP; an unknown key fails with the existing wording-reference error naming the key. | met | Keys `annotation.note` and `annotation.risk` exist in both tables (`Note`, `Risk`; `注記`, `リスク`, [tables](../../../src/chrona/resources/wording-tables-v0.1.yaml)); [`theme-v0.15`](../../../schemas/theme-v0.15.schema.yaml) takes the reference for `label` and `secondary`. [`test_annotation_kind_wording.py`](../../../tests/integration/test_annotation_kind_wording.py) renders a synthetic note and risk: ja-JP gives `リスク · Task 0`, `注記`, `リスク`, en-US gives `Risk · Task 0`, `Note`, `Risk`; a literal label is unchanged under both locales; a View `wording.keys` override reaches the reference; `annotation.nope` fails with `E_WORDING_KEY_UNKNOWN` naming `annotation.nope` ([pytest log](assets-1865/pytest-1865.txt)). Text in [Spec 07](../../specification/07-style-and-theme.md) and [Spec 63](../../specification/63-axis-name-tables.md). | — |
| 3 | The bundled presets adopt the new keys. This row is the reviewer's YAML edit in #1783, after rows 1–2 land. Expect 0 public SVG changes in en-US. | narrowed | Half adopted. [PR #1876](https://github.com/tya5/chrona/pull/1876) set `grouping.missing: {wording: grouping.unassigned}` in the shared [`design-default/view.yaml`](../../../src/chrona/resources/presets/bundles/design-default/view.yaml) (target-b, yuya, titlecard, marquee, sunday): en-US still draws `Unassigned`, ja-JP now draws `未割り当て` ([log](assets-1865/row1-3-render-locales.txt)). Not adopted: the Theme `annotationKinds` literals of the approved designs (target-b `label: RISK` / `NOTE`, yuya and sunday `label: RISK`, marquee and titlecard literal labels); on this main `target-b` under ja-JP still draws `RISK · test` and `NOTE · build` ([same log](assets-1865/row1-3-render-locales.txt)). PR #1876 states why: the sentence-case keys change en-US case and the ja-JP look of approved designs, so they wait for the owner comparison. These files are the reviewer's YAML (`src/chrona/resources/designs/**`), deferred to reviewer [#1848](https://github.com/tya5/chrona/issues/1848) / owner and to [#1783](https://github.com/tya5/chrona/issues/1783), which the issue names; this review does not edit them. | [#1848](https://github.com/tya5/chrona/issues/1848), [#1783](https://github.com/tya5/chrona/issues/1783) |

Counts: 3 rows, 2 `met`, 1 `narrowed`, 0 `not met`.

## Programme-level criteria (optional)

### Public side effects

This review adds a document, two small SVG renders, logs and nothing else under [assets-1865](assets-1865/pytest-1865.txt); it changes no code, schema, specification, guide, preset or example.

| Item | Slides changed | New diagnostics | Schema delta |
| --- | ---: | ---: | --- |
| This review | 0 | 0 | none |

The public effect of the reviewed PRs is in their own bodies.
