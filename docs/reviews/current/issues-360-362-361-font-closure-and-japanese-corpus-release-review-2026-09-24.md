# Font Closure and Japanese Corpus Release Review

Date: 2026-09-24

## Scope and published basis

This review accepts #360, #362, and #361 from the public `main` commits
`f8cd411`, `bf5e27c`, `4a57789`, `6860ad6`, `ac682f4`, `87a776c`, and
`7ea4f2b`. It reviews published artifacts only; no prior local work is a
release input.

## Acceptance evidence

| Requirement | Evidence | Result |
| --- | --- | --- |
| Small default and optional CJK provider (#360) | Primary resources contain data-driven Noto Sans Regular/Bold; `chrona-fonts-noto-cjk` is an entry-point provider; wheel smoke tests run on every CI OS. | Accepted |
| Closed metric/raster resolution (#360/#362) | v0.14 Context locators resolve metrics for SVG and font bytes only for PNG/PDF; materialization copies and rewrites only the target-required assets. | Accepted |
| Explicit authoring ingress (#360) | `chrona font import` tests cover static input, TTC selection, axis instantiation, collision rejection, descriptor resolution, and installed-wheel import. | Accepted |
| Draft-only substitute policy (#362) | `missingFont: substitute` produces the canonical warning ledger; immutable Context/materializer rejects it; absent non-fallback glyphs remain errors. | Accepted |
| Japanese public corpus (#361) | `examples/controller-z-ja/` pins Noto Sans JP through the provider, uses `ja-JP`, and commits materialized SVG evidence with long title, table, plot-label, and axis content. | Accepted |
| CJK raster path (#361) | The target registry renders the published Japanese corpus as SVG, PNG, and PDF using only its explicit descriptor; no host-font lookup is an input. | Accepted |
| Gallery disposition (#361) | `japanese-board` is a documented deferred entry: localized project/environment references cannot honestly satisfy the current same-reference one-axis pairing rule. | Accepted |

## Architecture review

The released dependency direction remains:

```text
font descriptor/provider -> Context closure -> Layout measurement -> completed Scene
                                                               -> SVG / PNG / PDF adapter
materializer -> copied and rewritten closure -> same pipeline
corpus evidence -> read-only gallery documentation
```

The importer is an authoring operation and is absent from the render path.
Package-provider lookup resolves declared resources only. Metrics remain the
only source of Layout geometry; adapters receive completed Scene primitives and
target-specific byte files, not Theme or Context discovery. The Japanese corpus
therefore exercises an ordinary declared face rather than a special rendering
branch.

## Verification

Focused local checks covered importer/CLI, font metrics, materializer,
Japanese CJK SVG/PNG/PDF targets, gallery inventory, gallery generation, text
encoding, and import direction. `tools/render_design_gallery.py --root .`
generated the tracked gallery pages; the resulting stale font-family diff in
the treatment page is an intentional reflection of the already-published
small-default migration.

GitHub Actions run `35958488175` on commit `7ea4f2b` passed on Ubuntu, macOS,
and Windows. Each job ran conformance, reachability/delivery/view/import/text
checks, the full parallel pytest suite, primary wheel build, installed-wheel
test, and outside-checkout smoke test with the CJK provider installed.

## Decision

All stated acceptance conditions are met. Close #360, #362, and #361. Future
localized gallery pairing requires an explicit gallery-contract design rather
than weakening semantic/environment identity checks.
