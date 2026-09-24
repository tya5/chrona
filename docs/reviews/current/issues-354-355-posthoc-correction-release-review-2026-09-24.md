# Issues #354 and #355 — Post-hoc Correction Release Review

**Decision:** Accepted

## Delivered correction

- Gallery validation now maps every Design Space dimension to its owned
  presentation references, requires an owner to change, and rejects each
  undisclosed changed reference with `E_DESIGN_GALLERY_AXIS_LEAK`.
- `halcyon-two-surfaces` uses the new
  `gallery-network-wallboard` Context: its Theme and Colour Scheme are fixed
  to the programme-board peer, while its View and declared Layout support
  differ.  The new SVG is committed materializer evidence.
- Deferred target selection is explicitly outside Design Space rather than
  falsely classified as Content.  Gallery pages identify their generator, and
  single-reference pairs include a normalized referenced-resource YAML diff.
- Corpus coverage now discovers only manifest/Context/Project-declared
  resources and reports bounded `enum`/`const` vocabulary for the four
  corpus-owning schemas, with explicit uncovered rows.  It remains non-gating.
- #358 records the separate portable Layout-token contract decision; this
  release does not mask that product debt through gallery metadata.

## Verification

- Focused correction tests: `9 passed`.
- `tools/corpus_coverage.py --check`, `tools/example_inventory.py`, and
  `tools/render_design_gallery.py --check` passed after regeneration.
- Chrona conformance and all module reachability, Scene primitive delivery,
  View dispatch reachability, and import-direction checks passed.
- GitHub Actions run 35943869610 passed on Ubuntu and macOS for `1eba4a2`.

## Architecture review

The correction preserves the one-way evidence chain from declared corpus
resources and source schemas to documentation.  Validator and report remain
maintainer tools with no runtime import edge.  The stricter gallery contract
does not add a rendering policy; it prevents documentation from asserting a
one-axis result where Context references prove otherwise.
