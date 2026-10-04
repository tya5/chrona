<!-- chrona:literal-acceptance/v1 -->

# Issue #1074: default actual gate symbol size, acceptance review

Source: [Issue #1074](https://github.com/tya5/chrona/issues/1074), re-fetched 2026-10-04 after the merges (body unchanged, 1018 characters; five comments: this work's claim, state and decision lines, and the owner decision recorded by the reviewer; no new acceptance rows). The rows below are the five literal bullets of its acceptance list. Work record: [issue-1074-actual-gate-symbol-default-2026-10-04.md](../../planning/active/issue-1074-actual-gate-symbol-default-2026-10-04.md); living contract [Specification 07](../../specification/07-style-and-theme.md) (symbol size).

Slices: design record [PR #1102](https://github.com/tya5/chrona/pull/1102) (`9ab9c373`); implementation [PR #1106](https://github.com/tya5/chrona/pull/1106) (`ebbf66b0`). The PR had conformance, three pytest shards, newest-Python reproduction and derived-ready green on its final head before merge.

**The default rule.** For the `actual` role only, an absent `symbolHeight` is `max(markHeight(actual), planned symbol height)` (the planned role's `symbolHeight`, else its `markHeight`); an absent `symbolOffset`, once the symbol is taller than the actual band, centres it on the planned symbol (otherwise `markOffset`). A declared value always wins. Reversal: a Theme declares `symbolHeight` equal to `markHeight` and `symbolOffset` equal to `markOffset` on `actual` (today's thin symbol, pinned by a test); globally, one function (`_default_actual_symbol` in [`surface_marks.py`](../../../src/chrona/presentation/layout/surface_marks.py)).

**Owner decision (2026-10-04, relayed by the reviewer through the lead):** change the default. The owner viewed the before and after crops and accepts the side effects listed under the corpus row; the numbering gap this leaves in the annotation list is a separate follow-up.

## Literal issue acceptance

### Issue #1074

- Source: [Issue #1074](https://github.com/tya5/chrona/issues/1074)
- Observed: 2026-10-04

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Bundled Themes (or the Layout default) give an actual gate symbol at least the planned gate's size. | met | The Layout default above, so bundled and user Themes alike. [`test_symbol_geometry.py`](../../../tests/integration/test_symbol_geometry.py) `test_without_the_tokens_the_actual_gate_is_as_large_as_the_planned_gate_and_on_it` (lane and automatic rows): the published actual Symbol has the planned gate's side and top. The regenerated corpus: in every one of the 55 Scenes that draw an actual gate (except `gate-symbols`, which declares both tokens) the actual side equals the planned side (4.8 to 8.0, 14.4 to 24.0, 6.0 to 10.0, 20.4 to 34.0, 14.0 to 36.0, 12.0 to 20.0 and 2.7 to 8.8 px). | none |
| 2 | Actual bars keep their `markHeight`. | met | [`test_symbol_geometry.py`](../../../tests/integration/test_symbol_geometry.py) (same test): the actual bar of the same fixture stays 0.6 of the track at offset 0.2; the corpus diff changes only `Symbol` primitives of the actual gate, never an actual `Rect`. Mutation "bar uses the symbol band" fails a test. | none |
| 3 | Corpus regenerated with a grouped diff review and images read (every slide with an actual gate changes). | met | Corpus regenerated with `tools/regenerate_public_examples.py --write`; 54 of the 55 Scenes drawing an actual gate change (55 on the final base, one slide being new), grouped by identical change in the [work record](../../planning/active/issue-1074-actual-gate-symbol-default-2026-10-04.md) section 7: (a) the actual gate alone (halcyon-1 editorial 13, technical print 14, target B 21, orion-asic gates, controller-z plan-only, halcyon-1 15, 17, 18); (b) the gate plus a relation path (controller-z-ja, controller-z annotation-border, annotation-rounded, slot-heading, halcyon-1 01, 08, 09); (c) the gate plus a member label and usually a relation path (halcyon-1 02, 11, 12, 16, 19, 20, aster-ssd overview, controller-z icons, material-icons); (d) the 23 controller-z slides that also move a relation label (executive and its variants); (e) the five slides with a suppressed or placed index, label or arrow (controller-z annotations, annotation-artwork, annotation-kinds, viewer-fit, baseline-ghosts, composition-compact). Accepted side effects (owner): the `firmware-slip` arrow of [`annotations`](../../../examples/controller-z/generated/annotations.scene.json) is suppressed with `W_LAYOUT_ANNOTATION_SUPPRESSED`, the `evb-note` index in annotation-artwork, annotation-kinds and viewer-fit and the `evb-highlight` index in annotations are suppressed, the `baseline-ghosts` Performance Characterization baseline label is suppressed, one `composition-compact` relation label that was suppressed is placed. The two tests that expected the arrow realized now pin its reported suppression. Images read before and after: halcyon-1 02 programme board, controller-z executive, annotations, halcyon-1 21 target B (after), 14 technical print (after), 13 editorial (after), 12 glyph gates (after), orion-asic gates (after), controller-z baseline-ghosts (after). Not read image by image: the other members of each group (listed above), controller-z-ja, aster-ssd overview, halcyon-1 01, 08, 09, 11, 15 to 20, and the remaining controller-z slides; they were measured primitive by primitive and each changes only what its group's read slide shows. | none |
| 4 | Contrast and perceptibility gates still pass. | met | The enlarged symbol has the same paint, so every Theme held to the floors passes the contrast and perceptibility gates (conformance green on the PR). The one new finding is target B's: the planned gate and the actual symbol both paint `#101828`, so the overlaid pair reads 1.000 against the mark floor 3.000; before #1126 that failed the derived pipeline, since [#1126](https://github.com/tya5/chrona/issues/1126) a Theme's contrast policy decides it (default warning, never blocking; target B is not in `conformance/contrast-opt-in.yaml`), so it is one warning. No gate or floor was changed here; the Theme is the reviewer's. | none |
| 5 | Synthetic tests with no `examples/` input; mutation check. | met | [`test_symbol_geometry.py`](../../../tests/integration/test_symbol_geometry.py): 14 tests on synthetic Projects through the packaged `executive-light` bundle (default size and centring in lane and automatic rows, restoring declaration equals the old size, planned tokens carried, declared height or offset with the other absent, a band taller than the planned symbol kept, the rule applied to `actual` only). Eight of eight mutations of the rule fail a test (default dropped, height or offset ignored, declared value overridden, centring dropped, applied to the baseline role too); an early return equivalent to the general path was removed rather than disclosed as a survivor. | none |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

Theme declares optional overrides (the two properties exist since #1066); Layout owns the default and the geometry in one function; Scene and adapters are unchanged. No schema change (no S0 run). The intended incompatibility is the migration above.

Disclosures:

- The issue's proposal also named the baseline (`snapshot`) gate; the design left it unchanged (a ghost may be deliberately smaller), which is not an acceptance row.
- A same-size actual gate on the planned date hides the planned diamond (paint order front); on different dates both show. Information is reduced, not lost: the actual diamond still marks the observed date.
- The technical-print slide now draws a 36 px black actual gate over the 36 px planned gate; this is the rule applied to that Theme's large planned gate and is reversible by the restoring pair.
- The coverage of an actual-facet endpoint spelling in `test_render_review.py` is reduced to the reported suppression of its annotation.

Exact review-bearing-main three-OS CI must pass before closing #1074; that run is recorded in the closing comment.
