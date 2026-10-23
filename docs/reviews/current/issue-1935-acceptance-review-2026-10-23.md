<!-- chrona:literal-acceptance/v1 -->

# Literal acceptance review: #1935 rows 1 to 4

Observed on `main` at `b88a81743` (the merge of [PR #1950](https://github.com/tya5/chrona/pull/1950), the single implementation PR). [Issue #1935](https://github.com/tya5/chrona/issues/1935) was re-fetched with `gh issue view 1935 -R tya5/chrona --comments` and `--json body,comments` on 2026-10-23 (4 comments) and counted literally. Rows 1 to 4 are the four numbered `Acceptance:` rows of the body. The four comments (the reviewer's placement after RC, the move into dev A's lane with the fast path, the move to dev B, and dev B's start note and decision record) add no acceptance row; the decision record states the chosen rule and the expectation of 0 public changes, which is checked under row 2.

The rule that landed: a placed annotation whose purpose has no leader style (`highlight`) and that declares `connector: leader`, or places a routed tail, keeps its box and text, draws no connector, and emits `W_LAYOUT_ANNOTATION_CONNECTOR_UNSUPPORTED_FOR_PURPOSE:<annotation-id>:<purpose>:<leader|tail>` once, at placement, in Layout. `connector: none` is silent and intentional. The rule is in [Spec 33](../../specification/33-intent-oriented-layout.md), paragraph "Connector support by purpose (#1935)".

## Method

Private venv `/private/tmp/claude-501/venv1682`, `PYTHONPATH=<worktree>/src:<worktree>:<worktree>/packages/chrona-fonts-noto-cjk/src` (absolute). Two worktrees: the parent of the #1950 merge (`55bbae053`) and `b88a81743` (this branch adds only this review, one test file and the logs).

- Reproduction of the issue (its fixture with the purpose changed to `highlight`), before and after: [repro-1935.py.txt](assets-1935/repro-1935.py.txt), [repro-1935-output.txt](assets-1935/repro-1935-output.txt).
- Public byte identity, independent of `tools.regenerate_public_examples --check`: every slide of every `examples/*/manifest.yaml` (50) was materialized with `tools.materialize_example.materialize` into a fresh directory on each tree, and the SHA-256 of each SVG and each Scene JSON (100 files) was recorded with [hash-public-slides-1935.py.txt](assets-1935/hash-public-slides-1935.py.txt): [parent hashes](assets-1935/public-hashes-parent-55bbae053.txt) and [after hashes](assets-1935/public-hashes-after-b88a81743.txt). `diff` of the two lists is empty.
- Tests: [pytest-1935-purpose-tests.txt](assets-1935/pytest-1935-purpose-tests.txt) (18 passed: the 16 combination cases of #1950 and the 2 routed-tail cases added here), [pytest-1935-neighbours.txt](assets-1935/pytest-1935-neighbours.txt) (331 passed: card fall-through, as-of fallback, render and the layout unit suite filtered to annotation, render and diagnostic tests), and [pytest-1935-tail-on-parent.txt](assets-1935/pytest-1935-tail-on-parent.txt) (the added routed-tail test run on the parent: the highlight case fails with no diagnostic, the note case passes).

Reproduction, on the issue's own fixture with `purpose: highlight` and `connector: leader`:

| tree | `annotation-box:view-n0` | `annotation-text:view-n0` | `annotation-leader:view-n0` | annotation/route diagnostics |
| --- | --- | --- | --- | --- |
| parent `55bbae053` | present | present | absent | none (silent loss) |
| `b88a81743` | present | present | absent | `W_LAYOUT_ANNOTATION_CONNECTOR_UNSUPPORTED_FOR_PURPOSE:view-n0:highlight:leader` |

## Literal issue acceptance

### Issue #1935

- Source: [Issue #1935](https://github.com/tya5/chrona/issues/1935)
- Observed: 2026-10-23

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | The selected purpose/connector contract is explicit in the living specification, including the relation to Spec33 mandatory rail leaders. | met | [Spec 33](../../specification/33-intent-oriented-layout.md), paragraph "Connector support by purpose (#1935)", directly after the mandatory rail leader paragraph. It states the purposes that carry a leader style (`callout`, `note`, `explanatory-arrow`) and draw a declared `leader`, that `highlight` has none, the exact diagnostic and its fields, that `connector: none` is silent, that a direct tail is drawn, that the render is not refused, and that "the diagnostic does not relax the mandatory rail leader of the purposes that have a leader style", which is the relation to the rail leaders. The code is a literal match: the rule at `surface_annotations.py` and the diagnostic text in `diagnostic_messages.py`. | — |
| 2 | Every supported combination emits its declared connector or its documented diagnostic/error; highlight+leader cannot silently disappear. | met | Table-driven test over 4 purposes, 2 connector kinds and 2 regions (rail, plot) in [`test_annotation_connector_purpose_1935.py`](../../../tests/integration/test_annotation_connector_purpose_1935.py): `leader` on `callout`, `note` and `explanatory-arrow` yields a leader in the Scene and the SVG with no warning, `leader` on `highlight` yields exactly one `...:view-n0:highlight:leader` warning, `none` yields no leader and no warning (all pass, [log](assets-1935/pytest-1935-purpose-tests.txt)). The routed `tail` is covered by the test added here, [`test_annotation_connector_purpose_tail_1935.py`](../../../tests/integration/test_annotation_connector_purpose_tail_1935.py): a routed tail on `note` draws a leader and warns nothing, on `highlight` it warns exactly `...:note-0:highlight:tail`. A direct tail on a `highlight` is box geometry that is drawn and is specified so. The silent loss is reproduced on the parent and closed on `b88a81743` (reproduction table above). The decision record's "0 public changes" is independently confirmed: SVG and Scene JSON of all 50 public slides have identical SHA-256 on `55bbae053` and `b88a81743` ([parent](assets-1935/public-hashes-parent-55bbae053.txt), [after](assets-1935/public-hashes-after-b88a81743.txt)). | — |
| 3 | Synthetic combination coverage preserves ordinary highlight behavior, intentional connector:none, full-body fitting and plot/tail safety. | met | Ordinary highlight: the box and text of a highlight are asserted present in the Scene and the SVG for `leader` and `none`, in the rail and the plot. Intentional `connector: none`: no leader and an empty warning list for every purpose. Full-body fitting: every case asserts the complete `BODY` text in an annotation text or list primitive. Plot safety: the `plot` region runs the whole matrix. Tail safety: the rule only adds a diagnostic after placement and changes no box, route or primitive, so no placement can regress; the 50 public slides (which include direct and routed tails) are byte-identical, the 331 neighbouring annotation, render and layout tests pass ([log](assets-1935/pytest-1935-neighbours.txt)), and the routed-tail path of the rule, which #1950 did not test, is now pinned by the test added in this PR (it fails on the parent, [log](assets-1935/pytest-1935-tail-on-parent.txt)). The routed-tail case uses the as-of opposite-side pass of the existing fixture of `test_annotation_asof_fallback.py`. | — |
| 4 | View/Theme/Layout own admission, paint and completed geometry respectively; Scene/adapters remain projection. | met | View admission is unchanged and still accepts the combination: `CONNECTOR_KINDS = {none, leader, tail}` in [`placement_candidates.py`](../../../src/chrona/presentation/model/placement_candidates.py) is not in the file list of #1950 (`spec 33`, `surface_annotations.py`, `diagnostic_messages.py`, one test), and the issue's fix path forbade reinterpreting intent. Theme owns paint: the absence of a leader style is `AnnotationPresentation(... leader_semantic_id=None)` for `highlight` in [`surface_quality.py`](../../../src/chrona/presentation/layout/surface_quality.py) (also not touched), which Layout reads and does not invent. Layout owns completed geometry and emits the diagnostic once, at placement (`_place_annotations_once` in [`surface_annotations.py`](../../../src/chrona/presentation/layout/surface_annotations.py)), keeping the box it placed. Scene and adapters only carry the diagnostic string: no Scene, adapter or SVG-writer file is changed, and the byte identity of the 50 public Scene JSON and SVG files shows no projection change. One reading is stated: the rule is a placement-time diagnostic, not an admission-time rejection, which the issue allowed ("documented diagnostic/error"). | — |

Counts: 4 rows, 4 `met`, 0 `narrowed`, 0 `not met`.

## Programme-level criteria (optional)

### Public side effects

This review adds a document, logs, a reproduction script, a hash script and one test file under [assets-1935](assets-1935/repro-1935-output.txt) and `tests/integration/`; it changes no behavior, schema, specification, guide, preset, design, example or workflow.

| Item | Slides changed | New diagnostics | Schema delta |
| --- | ---: | ---: | --- |
| This review | 0 | 0 | none |
| #1950, as measured here (100 files hashed) | 0 | 1 (`W_LAYOUT_ANNOTATION_CONNECTOR_UNSUPPORTED_FOR_PURPOSE`, raised only by a highlight with a leader or routed tail; none on a public slide) | none |
