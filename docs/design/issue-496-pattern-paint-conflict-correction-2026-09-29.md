# #496 pattern paint conflict correction

**Status:** Accepted before Slice 2 paint validation. **Authority:** Specification 07 pattern binding and Specification 08 Scene paint.

Catalogue pattern tile paths own stroke widths/caps/joins; Theme `stroke` is only ink color and `fill` is flat substrate. A role-level stroke width, dash, stroke finish, gradient, or non-fill background treatment would be ignored or conflict with these channels. Theme v0.13 rejects those combinations at the exact role-property pointer before Layout. Shadows and completed corner geometry remain independently supported. Existing non-catalog treatments retain their behavior; no version or issue acceptance change.
