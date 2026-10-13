<!-- chrona:literal-acceptance/v1 -->

# Source-selected legend progress review

## Literal issue acceptance

### Issue #1396

- Source: [#1396](https://github.com/tya5/chrona/issues/1396)
- Observed: 2026-10-13

The issue has no Acceptance heading; these are its verbatim Needed clauses.
Implementation and containing-review exact-main release acceptance are complete.

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | decide whether this is a real key/mark mismatch (fix the preset or the slide Theme) or an over-strict rule in the helper (fix the helper) | met | [Reviewer6105917044](https://github.com/tya5/chrona/issues/1396#issuecomment-6105917044): planned-source fills must not require an Actual inset. [PR1459](https://github.com/tya5/chrona/pull/1459) fixes the helper and makes the selected host's Plan/Actual key explain its fill, without corpus tuning. | — |
| 2 | add the corpus-wide run of the helper as a conformance gate so it cannot regress | met | [Checker](../../../tools/check_legend_keys.py) and [registration test](../../../tests/unit/tools/test_run_conformance.py) cover manifest-declared Scenes on all surfaces; CI applies its shared generated snapshot before conformance. Independently inspected snapshot11790703484 has46 Scenes and0 findings. | — |
| 3 | view one rendered legend as PNG. | met | Programme-board PNG was rendered with the explicit source resources and visually inspected. Plan's amber inset matches campaign progress; Actual remains green. Its emitted Scene passes the same checker. [Actual-SVG integration control](../../../tests/integration/test_legend_keys_match_marks.py) also checks matching source, paint and the missing-key negative. Reproduction command below. | — |
| 4 | Also: the shape-family check only covers the milestone role and no test breaks it; extend and add a breaking test. | met | [Synthetic tests](../../../tests/unit/tools/test_check_legend_keys.py) deliberately break planned/actual/snapshot/scenario span families (Symbol/Path), milestone family, paint presence/color, progress ownership and multi-surface isolation. | — |

## Programme-level criteria (optional)

- Selected architecture and implementation plan was published before code in
  [6138738719](https://github.com/tya5/chrona/issues/1396#issuecomment-6138738719).
  Layout owns the inset; Scene/adapters only project it. Spec61 states the source
  correspondence. Conformance/tests share one tooling implementation; no new
  entry, schema, resource kind or project-specific core policy.
- Focused45 integration/unit tests passed; subsequent32 checker/conformance tests
  and ready-base36 checker/conformance/literal-review tests passed. CI supplies
  full release coverage, not a duplicate local full suite.
- [PR1459 run38350914999](https://github.com/tya5/chrona/actions/runs/38350914999)
  succeeded on `f34d8687349411cf3e6e05e6daa66b5c2b858124`.
  PR1459 merged at `604e508543d5c314d33cd81ae504ad9f8de5a794`; synced READY
  `5e8ac499c3bd35af9d96f1fa98a11671a1a044c9` is superseded by corrected
  containing-review main85e66b4b and successful release38354040480 below.
  Snapshot11790703484: HALCYON02/12/15/19 each adds exactly one
  `legend-swatch:planned:progress-fill` primitive and one SVG node; all existing
  primitives, routes, diagnostics and viewport attributes are unchanged.
  Other public Scene/SVG bytes are identical, with0 additions/retirements of
  managed paths. The contrast report gains4 informational findings; errors stay0
  and warnings stay306. No authored examples or generated outputs changed.

## PNG reproduction

Run in the issue worktree's `.venv`; these are existing author resources:

```bash
.venv/bin/chrona render examples/halcyon-1/project.yaml \
  --view examples/halcyon-1/views/02-programme-board.yaml \
  --theme examples/halcyon-1/themes/wallboard.yaml \
  --scheme examples/halcyon-1/schemes/control-room-dark.yaml \
  --layout examples/halcyon-1/layouts/wallboard-programme-board.yaml \
  --actual examples/halcyon-1/actual.yaml \
  --summary examples/halcyon-1/profiles/summary-countdown.yaml \
  --detail examples/halcyon-1/profiles/detail.yaml \
  --viewport 1920x1080 --format png \
  --visual-profile chrona-output/visual/v0.7-png \
  --output /tmp/chrona-1396-programme-board.png \
  --emit-scene /tmp/chrona-1396-programme-board.scene.json
```

## Release disposition

Closed after [exact containing-review main85e66b4b release38354040480](https://github.com/tya5/chrona/actions/runs/38354040480)
succeeded on Windows/macOS/Ubuntu full pytest/conformance/wheel-smoke, MCP
and newest-Python public reproduction. The intermediate purity-test Windows
failure is corrected by PR1460; no product behavior was changed for that fix.
