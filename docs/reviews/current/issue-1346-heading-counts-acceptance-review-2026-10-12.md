<!-- chrona:literal-acceptance/v1 -->

# Issue 1346 — reusable count headings

Rendered acceptance and implementation CI are met. Release remains pending
the exact-main three-OS CI containing this review; the issue remains open.

## Literal issue acceptance

### Issue #1346

- Source: [Issue #1346](https://github.com/tya5/chrona/issues/1346)
- Observed: 2026-10-12

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | The three designs produce the same text on HALCYON from the template. | met | Real Title Card, Marquee and Sunday Contexts: template text equals original Scene and serialized SVG text, including `STATUS REPORTS : 03`. Nine-case evidence described below. | — |
| 2 | On the roadmap, they show its own counts. | met | Same templates and shared design resources: independent memberships resolve 26 items/6 groups/3 placed notes. Same-project 3-item/2-group controls change the rendered copy in all three designs; no copied Theme/Layout/Scheme. | — |

## Evidence and release gates

- Implementation: [PR #1432](https://github.com/tya5/chrona/pull/1432).
- Merged implementation: `c1095342bb574f8a41a9d0b3cede179bcd45a9b2`.
- Current-base head `8a654848edeb48e098359e4e274dda6e4aa7ca16`:
  [CI 38225129233](https://github.com/tya5/chrona/actions/runs/38225129233)
  passed on READY `f0e43199`, including reviewer PR1433: conformance,
  all three pytest shards, MCP floor and newest-Python reproduction passed.
- [Shared CI artifact](https://github.com/tya5/chrona/actions/runs/38225129233/artifacts/11736031116):
  all 92 public Scene/SVG files byte-identical to the current READY base;
  only diagnostic inventory and presentation coverage reports change.
- Reproducer: `python tools/heading_count_reuse_evidence.py --output-dir <empty-directory> --jobs 3`.
  All nine real Context/Scene/SVG cases pass. Local evidence:
  `/tmp/chrona-1346-integrated-reuse-NnnSYD/heading-reuse-evidence.json`.
- All 46 original full Scene/SVG pairs unchanged before reviewer-owned best
  declarations; integrated evidence:
  `/tmp/chrona-1346-integrated-materializers-p7Gtzt/materializer-evidence.json`.
- Post1433 count/policy/budget/ownership/schema probes: 127 focused tests pass.
  Shared definitions, schema annotations/precision guards and S0 pass.
- Review publication and exact-main three-OS release run: pending. Cite the
  terminal run in the issue closing comment after this review lands.

## Architecture conclusion

Core consumes neutral integer facts; Presentation closes immutable programs;
Layout binds before measurement and owns completed narrative receipts and
bounded count closure. Scene projects the accepted composition once.
Best/first-fit tests preserve every accepted invocation routing fact and discard
rejected whole-trial facts/progress. No generic error retry, guessed count,
geometry callback, Scene recount or compatibility factory remains. New formats
use shared frozen definitions and whole-member defaults. No authored examples,
presets or managed outputs are edited by this implementation. Permanent design
adoption remains reviewer-owned. Authority: Specs05/06/33/50/56 and the current
issue work record; no unresolved implementation architecture finding.
