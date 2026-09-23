# I310 Design Correction: Host-Specific Scheme Ink Intents

## Supersedes

This correction refines the Scheme-resolution sentence in
`i310-host-mark-inside-label-design-correction-2026-09-23.md`.  Its four
host-mark-specific semantic roles and the View → Layout → Scene ownership
remain unchanged.

## Trigger

Applying the approved roles to the public Themes showed that reusing the
existing `text` intent would require changing established Scheme text colours
to black for the executive and mission palettes.  That would silently alter
ordinary surface text merely to satisfy an inside-label contrast requirement.
It contradicts the prior correction's requirement that the existing semantic
palette retain its meaning.

## Corrected design

The Color Scheme contract declares four required, host-specific ink intents:
`insideLabelPlanned`, `insideLabelActual`, `insideLabelSnapshot`, and
`insideLabelScenario`.  They are colour values, not rendering instructions.
Each public Scheme supplies them without changing any existing intent.  The
last two may have equal values where snapshot and scenario marks share a fill,
but retain distinct names so a later Scenario visual role does not require a
contract migration.

Each Theme binds the matching `member-label-inside-<host>.fill` role to the
matching Scheme intent.  Theme resolution validates that role's resolved ink
against the resolved fill of its host mark with the existing 4.5:1 threshold.
The validation rejects an absent binding, non-colour binding, or unsafe pair
with `E_SCHEME_INSIDE_LABEL_CONTRAST`.

## Boundaries and architecture review

Scheme owns named palette values; Theme owns their visual-role bindings; Scene
only maps the completed Layout rung and already-known mark kind to one
semantic role.  Layout neither reads colours nor chooses a semantic role, and
renderers only serialize the completed Theme token.  Thus the correction
preserves the established presentation direction and avoids both palette-wide
side effects and renderer-local contrast policy.

No generic `textOnMark` intent is introduced.  The four intents encode the
real host distinction required by the contrast invariant, rather than a
reusable but under-specified foreground category.

## Implementation amendment

Extend the Color Scheme schema and resolver's closed intent set with the four
required colours.  Rebind public Themes to those names, retain their existing
`text` values, and add coverage for each pairwise host validation.  The
public inside-label example must exercise a successful explicit `inside` rung
and a short-mark fallback; `auto` remains outside-only.
