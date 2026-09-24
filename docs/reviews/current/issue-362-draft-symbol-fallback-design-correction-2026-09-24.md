# Issue #362 — Draft Symbol Fallback Design Correction

**Decision:** Accepted correction before implementation.

The selected small primary Noto Sans Regular/Bold pair does not contain U+2705
(`✅`).  Therefore it cannot satisfy #362's explicit draft-substitution
acceptance by itself.  Measuring `.notdef` would violate the declared-metrics
contract, and using a host emoji font would violate the immutable/offline
resource boundary.

The primary distribution additionally packages a metrics-only, one-glyph OFL
Noto Color Emoji subset for U+2705 as the **draft substitution fallback**, not
as a Theme typography face.  Its source TTF is subset reproducibly before
metrics generation; only its tiny metrics record, source identity, and OFL
notice ship.  It is not selected by any public Theme, is not copied into a
strict Context, is not passed to PNG/PDF, and has no Scene or SVG policy effect.
When `missingFont: substitute` is selected at draft ingress, Layout first
measures the requested declared face and then this explicit fallback metrics
record for an otherwise unavailable glyph.  The warning names both families,
the code point, requested weight, and source text.  If the fallback record also
lacks the glyph, rendering still rejects.

This retains the primary-wheel limit below 5 MB, keeps the default Latin pair
as the normal zero-setup face, and makes the requested `General Availability
✅` behavior truthful without widening the strict evidence closure.
