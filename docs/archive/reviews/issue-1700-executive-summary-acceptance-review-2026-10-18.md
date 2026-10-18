<!-- chrona:literal-acceptance/v1 -->

# Executive summary acceptance review

## Literal issue acceptance

### Issue #1700

- Source: [Issue #1700](https://github.com/tya5/chrona/issues/1700)
- Observed: 2026-10-18

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic: a depth-1 rollup with nested gates keeps the gates (or emits a pointed diagnostic naming them), and draws exactly one summary mark per group. | met | [Depth0/1/all and Snapshot Model cases](../../../tests/unit/chrona/presentation/model/test_projection_rows.py); [native overlapping-date gates, separate bands, labels, comparison and relation-port tests](../../../tests/integration/test_first_run_hierarchy.py); [clipped primary-summary geometry](../../../tests/unit/chrona/presentation/layout/test_surface_window_marks.py). | — |
| 2 | A guide section shows a one-page executive summary from an imported CSV. It runs in the docs tests and renders with at least default, executive-light and mission-light. | met | [Guide](../../guides/executive-summary.md) and [executed literal commands](../../../tests/integration/test_executive_summary_guide.py); all three native SVGs contain both full gate captions. Mission-light uses its bundled preset with a documented project-local Layout override, not a modified shipped preset. | — |
| 3 | A count table and PNGs. | met | [Pinned before/after counts, five inspected PNGs and exact inputs](https://github.com/tya5/chrona/tree/7e91d0f2619bb49319f9e47b1c6b49ed596067d1/review-evidence/issue-1700), source `f172dfb0be65fd01d650bd166b3e85e2cb761d08`; [final PR artifact 12134891226](https://github.com/tya5/chrona/actions/runs/39121608414/artifacts/12134891226) from source `5f78fe6d071127b3177c57af45e2f77c8e7d83a4` matched all109 reviewed payloads, with only the two intended overlay removals. | — |

## Release evidence

Implementation merged as PR [#1714](https://github.com/tya5/chrona/pull/1714)
at `1c440a8014c81ab99fad3a51f9d5d11eb8addcd4`; its final CI run
[39121608414](https://github.com/tya5/chrona/actions/runs/39121608414) passed.
The exact-main release at `bd499a5a13d909cad6dd34282c17a4ee76ca6c74`,
[39123129369](https://github.com/tya5/chrona/actions/runs/39123129369), also
passed all required gates:

- Linux: 13,574 passed (9,693 + 3,881 across the two test phases), 70 skipped.
- macOS: 13,579 passed, 65 skipped.
- Windows: 13,571 passed, 73 skipped.
- Conformance, OS probe, wheel build/size check (4,372,773 bytes), installed-wheel
  smoke and CI outcome checks passed on all three operating systems.
- MCP floor: 33 + 53 tests passed; newest-Python 3.12.15 public reproduction: 1 passed.

Focused Model/Layout/Scene/native/docs tests pass181. The five reviewed native
PNGs and pinned count table are linked in criterion 3. Final PR artifact
12134891226 was checked against all109 reviewed payloads; the intended public
change is removal of the duplicate summary overlay. No generated files or test
assertions were hand-edited.

[Pre-code design/architecture/implementation plan](https://github.com/tya5/chrona/issues/1700#issuecomment-6248519700)
and normative correction `bba2cf919` precede code `05695184a`.
Model closes retained membership without changing Core ancestry or inferring
attachments; ordinary track policies are preserved, not forced to shared.
Layout owns completed marks, clipping, fitting and routes. Removing the duplicate
shape does not remove comparison facts or the primary relation host. Scene and
adapters acquire no hierarchy or placement responsibility. Specs06/38 record
the intended depth/overlay migration; no schema or corpus-resource adaptation.
