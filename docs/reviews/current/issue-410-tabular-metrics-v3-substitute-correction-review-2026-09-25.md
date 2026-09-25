# Architecture Review — #410 I410-2 Substitute Capability Correction

**Correction reviewed:** `ebc5e0a3`.

The correction preserves the authority boundary.  A numeric feature is a
capability of the selected primary font face, while a draft glyph substitute is
only a per-character measurement fallback.  Allowing the substitute to invent
digit metrics would make it an alternate font-selection policy; rejecting it
for lacking unrelated digits would couple emoji fallback to table semantics.

Implementation must therefore represent optional numeric maps on substitute
metrics, validate complete maps before a primary treatment is accepted, and
never use fallback advances for a numeric digit.  The existing warning record
continues to disclose every substitute glyph.  No Context, Scene, or adapter
ownership changes are required by this correction.

**Result:** accepted.  Resume I410-2 implementation with this constraint.
