# Issue 1178: multipart mark contrast acceptance

Implementation: `260219c677d2106067d0550efa1620859b3b4161`.
[Current design, architecture review and implementation plan](https://github.com/tya5/chrona/issues/1178#issuecomment-6007896714).
Released on `6df8bcbaea1a990c01c42582cd46852bef2f4ec4` through PR #1179.
[Exact-main release](https://github.com/tya5/chrona/actions/runs/37406723077)
passed: macOS 7315/61, Ubuntu 7311/65, Windows 7310/66 (passed/skipped);
three-OS conformance, wheel/smoke, MCP floor and newest-Python materializers.
Issue #1178 closed as completed on 2026-10-06 after all four literal rows met.

## Architecture and verification

Spec 46 owns this completed-Scene observer. Exact placement identity groups
MARK Symbols only; both completed part-ID forms are supported. Source/role
alone cannot merge marks. Layout, paint, adapters, schemas and resources are
unchanged. Artwork layers retain their independent touched-ink obligations.
Structural and unsupported-ground failures remain fail-closed. Pattern pairs
retain their worst-pair obligation before figure-level visibility selection.
Independent Luna review found no remaining contract mismatch.

Focused tests: 162 existing contrast/artwork/severity/render tests and 17 new
[multipart fixtures](../../../tests/unit/chrona/presentation/scene/test_multipart_mark_contrast.py)
passed in the worktree venv. Full pytest and generated release evidence belong
to CI, not a duplicate local suite.

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | A glyph with parts of equal or similar ink on a contrasting ground yields 0 mark findings. | met | Multipart fixtures cover both ID forms: no warning/error finding, one successful info observation against external ground; equal and contrasting part/channel inks retain actual evidence identity. | — |
| 2 | The same glyph on a ground equal to its ink yields **one** finding for the figure, not one per part. | met | Multipart fixtures: one ratio-1 figure error, one warning under the default Theme policy, actual part/ground identity; malformed paint and unsupported ground cannot be hidden by another part. | — |
| 3 | Single-part marks are unchanged, and other Themes produce byte-identical diagnostics. | met | Exact singleton mapping fixture; independent placements/surfaces/roles and artwork boundaries. All 64 public contexts retain serialized non-info contrast mappings. [CI artifact 11385929396](https://github.com/tya5/chrona/actions/runs/37403565104/artifacts/11385929396) matches all 137 final-main generated files; 128/128 Scene/SVG bytes unchanged. Only inventory positions and 10 redundant `12-glyph-gates` info observations change (159→149); every warning/error report row is exact. | — |
| 4 | In Yuya, the lantern-gate mark warnings drop from 65 to the real figure-versus-board cases, if any. | met | Actual [reviewer artifact 11387920834](https://github.com/tya5/chrona/actions/runs/37407126850/artifacts/11387920834), exact head `f2f88c1d7d26f4a8f82b7e7f5e51b60e46964602`, versus prior artifact 11385697511: multipart warnings 57→2; serialized mark diagnostics 65→10. Retained actual CDR vs planned CDR ratio 1.640435 and planned launch vs launch-window ratio 1.175068 are external-ground cases. SVG bytes, all geometry/paint, non-mark diagnostics and non-figure report rows unchanged. | — |

The revised Yuya artifact's 65 is its total mark-warning count, not 65
same-glyph warnings. No reviewer YAML was changed. Observer adoption is proven
by the current artifact; whole-target visual sign-off remains reviewer-owned
under #1116. The closing comment links the immutable review and exact-main CI.
