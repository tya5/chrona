<!-- chrona:literal-acceptance/v1 -->

# Bounded table acceptance (#1295)

[Current design, architecture and implementation record](https://github.com/tya5/chrona/issues/1295#issuecomment-6094464024). Authority: Specs24 section2.1, 33 sections6/8, 50 section3.1. Packaged migration: `8ca3aa79`.

## Literal issue acceptance

### Issue #1295

- Source: [Issue #1295](https://github.com/tya5/chrona/issues/1295)
- Observed: 2026-10-11

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A test with one title far longer than the canvas. From the Scene, the table's inline extent stays within the declared bound and the plot keeps the rest. The long title's cell has more than one line (or an ellipsis plus a diagnostic). No `W_LAYOUT_VISIBLE_OVERFLOW` for the title. | met | [All packaged preset Scene/SVG tests](../../../tests/integration/test_packaged_bounded_table.py) and [bounded render tests](../../../tests/integration/test_bounded_table_render.py) cover long title/cell wrapping, source-linked ellipsis, share ceiling, retained plot and no title overflow; actual View YAML supplies the intent. | — |
| 2 | The same project with short titles produces the same Scene as today. | met | [Packaged fitting-copy tests](../../../tests/integration/test_packaged_bounded_table.py) compare whole SceneSurface and SVG bytes with only the new wrap/share declarations absent; every library preset passes. Truthful migrated resource identities are separate from unchanged geometry/paint/routes/diagnostics. | — |
| 3 | Do not edit `examples/**`. | met | [Packaged implementation](https://github.com/tya5/chrona/commit/8ca3aa79): `git diff --name-only origin/main...HEAD -- examples` is empty for authored work. | — |

## Programme-level criteria (optional)

Current preparation adopts READY main `477e571d` (merged PR1410 and its
verified generated snapshot) by ordinary merge. The adjacent schema additions
retain both table-only `maxInlineShare` and legend `columnDistribution`;
no policy collision, checker exemption or authored examples change.
Current-head table/render/packaged/measurement/placement/heading/share batch:
159 passed (28.47s). Prior adjacent default/window/axis/legend integration:
120 passed (54.77s); UTF-8 default-date checks15 passed (2.82s).

Current full schema comparison against `9ea350d5`: Layout/Scene/View delta=3,
equal=35,482 documents (378 mapped),739 probes, four known-invalid fixtures
unchanged. The sole failure is L2+L3=85.6s against the unchanged60s budget;
semantic agreement is not a green gate. CI must pass the strict gate, with
no local timing waiver or baseline refresh.

Public head `49cfb0ef`, run38124948692 artifact11696806849, verified ZIP
SHA256 `54ee9326181efa4187ef92938402a32319a226c2e19f82b973b3a9ed61087050`:
101 paths, no additions/removals, all46 Scene/SVG pairs byte-identical;
only diagnostic inventory and coverage reports change. Strict CI schema gate
passes (20.58s). Conformance fails on eight unclassified exact-Decimal
sums. The reviewed function+explicit-Decimal-seed classification locally passes
with97 focused tests (4.87s), including rejection of unseeded/float-seeded sums;
that classification changes no product code or golden output.
All three PR shards are terminal: 37 failing tests, including the checker.
Additional families are derived-axis/header dependency loss (3), nested
content-sized heading budgets (26), cramped CLI/agent rendering (3), frozen
Scene identity checks (3), affix allocation (1), and the precision checker (1).
Original failures are dispositioned below, not waived by a baseline refresh.
Candidate-local heading measurement now
reuses closed render metrics instead of deriving them from a one-source
subset: derived-size/source-sizing/source-measurement batch33 passed (12.22s),
including an immutable metric-reuse regression. Correction source commit:
`701c6bec` (prepared from the identical local tree). Corrected-head CI and
snapshot remain required.
Frozen Scene identities are independently dispositioned: render the same three
synthetic scenarios using exact View/Layout resources from READY477e571d.
Old Scene hashes48989414/445031fb/f26aa795 are reproduced; current hashes
52e5f188/5e027fbe/d5752026 differ only in provenance. All three complete Scenes
are otherwise identical and actual SVG bytes are identical. Only those three
Scene expectations change; unchanged SVG hashes and semantic assertions remain.
The three exact characterization tests pass (4.25s).
Fitting intrinsic headings retain natural demands; closure selection uses
native Decimal source/ancestor extents, never float reporting warnings or an
unrelated sibling's overflow. Seven new nested-host/independent-long-heading/
unrelated-sibling cases accompany heading/region-frame batch104 PASS33.12s and
bounded/source/packaged batch65 PASS21.58s. Strict circular table gates remain.
Affix allocation follows published Spec24:80px retains `…!!`;20/40/60px
reject impossible mandatory columns. All18 affix tests pass (12.42s).
Warning-envelope tests use an explicitly uncapped local preset; a separate
300px default test proves typed E_LAYOUT_TABLE_OVERFLOW and no output file.
No production tiny-viewport exception. The complete failed-family regression
batch now passes329 tests (144.23s), including all previously failing test
files, new negative cases and the precision checker. Float checker separately
passes. Exact-head CI must still prove the full PR and generated output gates.
A baseline gate label that already overflowed is not fitting-copy
evidence: opt-in ellipsis changes it intentionally. Release remains pending:
current-head PR checks and review-containing exact-main
three-OS release. These local rows do not authorize closure.

## Architecture conclusion

View normalizes closed wrap intent once; Layout closes immutable source facts at each actual candidate width, honors authored minima, applies the declared share, measures heading independently and emits completed lines/ellipsis with source diagnostics. Scene/adapters never allocate or measure. Existing budgets/closure serve fixed, flexible and Grid hosts; no project-specific conditional, font reduction or plot-label policy was introduced. Preserve the independent #1294 axis migration during final integration.
