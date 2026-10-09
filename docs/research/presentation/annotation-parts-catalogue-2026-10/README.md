# Annotation parts catalogue: `chrona-annotation-parts-v2026-10-09`

This additive catalogue contains the two original monochrome layers used to
compose a hanging-scroll container: `scroll-mounting` (hanger and mounting
ring) and `scroll-rods` (upper/lower rods and knobs). They are independent
48×64 glyphs in the `chrona-annotation-parts` set. The target-parts catalogue
has a v0.5 successor, `chrona-target-parts-v2026-10-09`, which adds seigaiha;
the former catalogue is archived byte-for-byte.

The four packaged resource files live in `src/chrona/resources/icons/`:
authored source YAML, canonical `icon-catalog/v0.5` YAML, manifest, and MIT
notice. A Theme uses `chrona-annotation-parts:scroll-rods` (or
`chrona-annotation-parts:scroll-mounting`) through an explicitly pinned
Context catalogue; the renderer does not discover catalogues implicitly.

Reproduce the source with:

```bash
python docs/research/presentation/annotation-parts-catalogue-2026-10/build_source.py
```

Import it with `chrona icon-catalog import --theme-assets
src/chrona/resources/icons/chrona-annotation-parts-v2026-10-09.source.yaml
--output src/chrona/resources/icons/chrona-annotation-parts-v2026-10-09.yaml`.
Render `gallery.py` to inspect both glyphs at 64px and 20px in light and dark
Theme tokens.
