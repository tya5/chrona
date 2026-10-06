# Issue 1178: multipart mark contrast acceptance

Implementation: `260219c677d2106067d0550efa1620859b3b4161`.
[Current design, architecture review and implementation plan](https://github.com/tya5/chrona/issues/1178#issuecomment-6007896714).
Product and review release gates are pending; keep the issue open until CI on
the exact published commit containing this review succeeds.

## Architecture and verification

Spec 46 owns this completed-Scene observer. Exact placement identity groups
MARK Symbols only; both completed part-ID forms are supported. Source/role
alone cannot merge marks. Layout, paint, adapters, schemas and resources are
unchanged. Artwork layers retain their independent touched-ink obligations.
Structural and unsupported-ground failures remain fail-closed. Pattern pairs
retain their worst-pair obligation before figure-level visibility selection.
Independent Luna review found no remaining contract mismatch.

Focused tests: 162 existing contrast/artwork/severity/render tests and 15 new
[multipart fixtures](../../../tests/unit/chrona/presentation/scene/test_multipart_mark_contrast.py)
passed in the worktree venv. Full pytest and generated release evidence belong
to CI, not a duplicate local suite.

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | A glyph with parts of equal or similar ink on a contrasting ground yields 0 mark findings. | met | Multipart fixtures cover both ID forms: no warning/error finding, one successful info observation against external ground; equal and contrasting part/channel inks retain actual evidence identity. | — |
| 2 | The same glyph on a ground equal to its ink yields **one** finding for the figure, not one per part. | met | Multipart fixtures: one ratio-1 figure error, one warning under the default Theme policy, actual part/ground identity; malformed paint and unsupported ground cannot be hidden by another part. | — |
| 3 | Single-part marks are unchanged, and other Themes produce byte-identical diagnostics. | met | Exact singleton mapping fixture; independent placements/surfaces/roles and artwork boundaries. All 64 current public contexts have identical serialized non-info contrast mappings before/after. Only `12-glyph-gates` analysis observations change from 159 to 149; its public mark diagnostics remain unchanged. CI verifies regenerated Scene/SVG bytes. | — |
| 4 | In Yuya, the lantern-gate mark warnings drop from 65 to the real figure-versus-board cases, if any. | met | Read-only [reviewer artifact 11385697511](https://github.com/tya5/chrona/actions/runs/37402192306/artifacts/11385697511), exact head `41df790d55f86cab2130909184380d0d4d8b4e0c`: grouped warnings 57→2; all mark warnings 65→10. Retained actual CDR vs planned CDR ratio 1.640435 and planned launch vs launch-window ratio 1.175068 are external-ground cases. All non-figure observations unchanged. | — |

The revised Yuya artifact's 65 is its total mark-warning count, not 65
same-glyph warnings. No reviewer YAML was changed and actual Yuya adoption is
not claimed. The CI snapshot must confirm corpus/report deltas; the closing
receipt must cite the successful exact-main release and immutable review link.
