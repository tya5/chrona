# Design Correction: Detail Profile and Layout Closure (#350)

**Status:** Superseded in part — see Optional Detail Regions and Context Closure correction.

## Finding

`normalize_v05_surface_content` previously received no solved Layout manifest.
As a result, a bound detail profile could silently lose group details,
milestones, and observations when the active layout omitted their slots. Once
the correct manifest is supplied, the established detail resolver correctly
rejects that incomplete closure. Controller Z currently exposes this mismatch.

## Corrected contract

A bound detail profile and its selected Layout are one materializable closure:
every declared `groupDetails`, `milestones`, and `observations` section requires
the corresponding Layout source slot; every required source slot requires its
profile section. The render use case always passes the solved manifest to the
normalizer. It never silently drops detail facts.

The Controller Z executive layout is extended atomically with the three detail
slots and its generated public evidence is regenerated. The follow-up
correction defines their optionality for contexts that do not bind Detail.
This is not a compatibility bridge: malformed bound profile/layout pairs
reject before Scene.

## Architecture review

The correction restores the existing authority chain: Detail Profile selects
facts, Layout declares available regions and computes placements, Scene only
projects. It prevents a View visual target from appearing valid while its
source text is silently absent, and it introduces no fallback or adapter-local
selection.

## Acceptance

- every published Context with a detail profile materializes only when all
  declared detail sections have slots;
- Controller Z emits group-detail and milestone placements from its bound
  profile, with no silent omission;
- a missing slot/profile pair rejects before Scene;
- the complete visual target fixture projects group-detail and milestone icons
  from the corrected closure.
