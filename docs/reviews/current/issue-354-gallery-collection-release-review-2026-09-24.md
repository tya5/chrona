# Issue #354 — Gallery Collection Release Review

**Decision:** Accepted

## Published collection

The generated v0.2 gallery contains five evidence-backed comparison sets and
eleven documentary entries:

| Set | Dimension | Evidence |
| --- | --- | --- |
| Executive status | Content | Controller Z executive / plan-only |
| Treatment ladder | Appearance | Controller Z executive / elevated Theme treatment |
| Two surfaces | Content + disclosed Layout support | Halcyon programme board / dependency network |
| Colour scheme | Appearance | Halcyon mission light / control-room dark / print mono |
| Investigating a slip | Content | Halcyon scenario / captured baseline |

Each entry resolves to a declared manifest slide, immutable Context reference,
and committed materializer SVG. The catalogue validator proves semantic
Project/Actual equality inside each set, target/capability claims, one declared
dimension/axis, and declared evidence existence. Generated set pages disclose
only presentation-reference differences and never become render input.

## Deferred evidence

The gallery index names, rather than hides, the remaining proposed sets:
responsive programme-at-scale needs a compatible View/Layout design; slot and
encoding sets need their own presentation designs; Japanese typography is
blocked by #351; and multi-target evidence needs a manifest contract. The
attempted existing-resource programme pair was rejected with
`E_LAYOUT_TOKEN_UNKNOWN` and `E_LAYOUT_TABLE_OVERFLOW`; the attempted network
View under a table Layout was rejected with `E_PRESENTATION_PRIMITIVE_MISSING`.
No invalid Context or fabricated SVG was retained.

## Verification

- `tools/corpus_coverage.py --check`, `tools/example_inventory.py`, and
  `tools/render_design_gallery.py --check` succeeded.
- Conformance and all structural gates succeeded.
- Local full pytest: `613 passed, 13 skipped`.
- The public materializer reproduction suite covers every declared corpus
  slide, including the two new Halcyon appearance peers; generated SVG changes
  were reviewed as one batch.
- GitHub Actions run `35942283962` for `4b54f56` succeeded on Ubuntu and macOS,
  including parallel tests, wheel build/install, and isolated smoke testing.

## Architecture conclusion

The implementation preserves the one-way corpus → gallery documentation flow,
the Specification 55 ownership taxonomy, and #348's package deferral. The
collection is ready to grow only through an approved design for a deferred
set; it has not introduced a gallery resolver, a renderer path, or a second
presentation format.
