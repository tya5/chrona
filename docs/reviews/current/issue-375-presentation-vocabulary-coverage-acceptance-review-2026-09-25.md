# Acceptance Review: Presentation vocabulary coverage (#375)

**Decision:** Accepted, pending final three-platform CI.

## Delivered boundary

`tools/presentation_coverage.py` is a deterministic, read-only curation
report.  It reads the declared corpus Context closure, the schema inventory's
four live presentation contracts, and checked-in `chrona/scene/v0.2` artifacts.
It neither imports Chrona producer modules nor parses SVG.  The report records
the 20 source Scene artifact paths, live contract versions, finite schema
vocabulary evidence, and separately declared / placed / realized slot sources.
`docs/gallery/README.md` links it through its owning gallery generator.

The resulting evidence names all requested detail sources.  It does not claim
that they are uniformly absent: `milestones`, `annotations`, and
`group-details` have real current evidence; `observations` is the one declared
slot source not yet realized.  The live `overlay` grammar remains uncovered,
which is the intended input to #382.

## Scene and placement correction

The new consumer exposed the missing primitive-to-slot fact in Scene v0.1, so
#375 published Scene v0.2 and migrated all corpus evidence.  During final
testing, three optional-annotation draft cases exposed an incomplete icon owner
fallback.  The published correction plan, design, architecture review, and
implementation plan restored the Layout boundary: every icon receives its
host's resolved Layout slot, candidate annotation icons receive their explicit
annotation slot, and no Scene fallback or ID/geometry inference exists.

This is compatible with the architecture: View declares intent, Layout owns
geometry and allocation, Scene projects completed placements, and coverage only
reads serialized facts.  No presentation policy or View syntax changed.

## Verification

| Gate | Result |
| --- | --- |
| I375-focused materializer / Scene / use-case / coverage tests | `51 passed` |
| Icon-owner correction focused suite | `15 passed` |
| Public materializer / adapter / use-case reproduction | `35 passed` |
| Generated reports and diagnostics | all `--check` gates passed; no worktree artifact diff |
| Conformance and structural checks | conformance passed; 75 reachable modules, 32 delivered Scene fields, 10 View values, 9 inward-only packages |
| Full suite | `761 passed, 18 skipped` |
| Wheel | 2,487,279 bytes, below 5,000,000-byte limit; isolated installed-wheel smoke passed |

The only full-suite warnings are the pre-existing `jsonschema.RefResolver`
deprecation warnings.  Final close requires the CI run for this acceptance
commit to pass on Ubuntu, macOS, and Windows.
