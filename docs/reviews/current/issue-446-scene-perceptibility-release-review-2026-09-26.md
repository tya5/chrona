# Release Review — Serialized Scene Perceptibility Gate (#446)

## Acceptance evidence

| Requirement | Evidence | Result |
| --- | --- | --- |
| Pure serialized-Scene evaluator | `scene.perceptibility` accepts mappings only; its focused fixtures cover occlusion, typed hosts, slot disposition, intersection threshold, composited paint, ordering, and malformed input. | Pass |
| No new policy owner | `tools/check_import_direction.py` passes; evaluator imports no Layout, font metric, renderer, or raster module. | Pass |
| Public corpus has no unpermitted finding | `tools/check_scene_perceptibility.py --format json`: 21 committed Scenes, 0 `E_` findings; 24 individually emitted declared visible-overflow observations. | Pass |
| Gate runs once and reports independent outcome | `scene-perceptibility` occurs once after generated-evidence inventory in the #451 catalog; focused runner test and conformance pass. | Pass |
| Draft feedback preserves completed artifact | Draft-only `W_SCENE_*` transport retains original finding code, Scene path, primitive IDs, slot, disposition, and measured facts; immutable paths do not add it. | Pass |
| Public materializer/release gate | GitHub Actions `36178035082`: Linux, macOS, Windows, wheel smoke, and newest-Python public materializer reproduction all pass. | Pass |

## Corpus disposition

The gate records no numeric failure baseline.  Each visible-overflow observation
is classified from its own completed slot policy.  Paint observations are
available in the machine report for #431; no contrast threshold was selected by
this issue.  No SVG, Scene, or materializer evidence byte changed as a side
effect of adding the observer.

## Architecture conclusion

Layout remains responsible for geometry and fit policy; Scene remains the
completed transport; adapters remain serializers.  The evaluator observes the
published Scene and only its error findings become draft feedback after the
artifact is completed.  #446 is accepted.
