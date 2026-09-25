# Architecture Review — #410 I410-2 Tabular Metrics v3

**Design reviewed:** `e6e40ede`.

## Overall-design alignment

| Boundary | Reviewed decision | Result |
| --- | --- | --- |
| Font resource → Layout | v3 records both feature-selected digit maps under the exact face identity. | Pass |
| Theme → Layout | Theme selects only finite `numericSpacing`; it neither inspects tables nor measures text. | Pass |
| View → Layout | `signedDays` remains a semantic format; it does not gain a font-feature field. | Pass |
| Normalization → Layout | A normalized table cell carries its semantic text role, allowing per-cell measured allocation. | Pass |
| Layout → Scene | Completed numeric spacing and bounds remain on placement/Scene data. | Pass |
| Scene → adapter | SVG/Typst/TikZ serialize supplied feature choices and do not inspect font resources. | Pass |

## Findings and required controls

1. **Do not use cmap defaults as a feature proxy.** Noto Sans demonstrates why:
   default digits are tabular while `pnum` changes their advances.  v3 must
   contain both maps and resolver validation must make a selected mode
   unavailable if either map is incomplete.
2. **Keep column allocation renderer-neutral.** A single `font_size` argument
   is no longer sufficient once cells can have a numeric role.  Replace it with
   a Layout-owned measurement callback; do not special-case `signedDays` in the
   allocator or Scene builder.
3. **Do not silently make all roles tabular.** The `numeric` role is selected
   only for normalized signed-day table cells.  Other text remains the Theme's
   explicit proportional treatment, including its selected output feature.
4. **Make the migration atomic.** Context v0.16, descriptor algorithm v3,
   package metric identities, public Contexts, HALCYON Themes, and generated
   evidence must land together.  Dispatch must remove v0.15 rather than
   maintaining two live resolution paths.
5. **Feature syntax is projection, not authority.** Adapter tests must assert
   the supplied mode but no renderer may import `font_metrics`, parse OpenType,
   or calculate an advance.

## Review conclusion

The detailed design preserves the programme's authority chain and repairs the
otherwise invisible pnum/tnum measurement-versus-paint mismatch.  It introduces
one justified normalization field (`TableCellContent.typography_role`) and no
new cross-layer policy.  Implementation may proceed only through the atomic
v3/Context migration and public evidence gate described in the implementation
plan.
