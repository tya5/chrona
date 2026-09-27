# Architecture Review — Image-Backed Annotation Container (#465)

**Decision:** design conditionally approved for implementation planning,
pending one lead/owner confirmation (below). **Reviewed design:**
[#465 contract](../../design/issue-465-image-annotation-container-design-2026-09-27.md).
**Normative update:** Specification 65 (new, Proposed) and additive
paragraphs in Specifications 64 and 07. This is a design review, not issue
acceptance.

## Whole-system consistency

| Boundary | Authority checked | Result |
| --- | --- | --- |
| View | Specification 24/33/44 View grammar; #466 candidate design | No new syntax. A View still authors only text/anchor/purpose/candidates; it cannot name an image, an asset catalog, or an inset. Acceptance bullet 1 ("A View cannot") holds structurally, not by a runtime rejection, because the new asset family has no View-facing grammar at all. |
| Theme | Theme v0.11 `annotationContainer` (#466 C2); Specification 07 §annotation container | Additive third `outline` value on an existing token, following the exact `if/then` schema pattern `tailBaseEm` already uses for `balloon`. The 466-landed `rectangle`/`balloon` branches are untouched; `annotation_container()`'s existing two-branch callers gain a third branch, not a signature break. No Theme version bump (repository precedent: `progressInset` #430, `chipPadding` #428). |
| Icon catalogs / Specification 64 | §1 scope statement, §3's reserved "separately designed asset family" | Specification 65 is written as that reserved family: a sibling resource kind, not a `chrona/icon-catalog/v0.3` entry type. This keeps spec 64's own stated boundary ("does not own... arbitrary images/artwork") intact and keeps a View's `visuals` grammar unable to reach container art. Flagged below as the one point needing explicit confirmation, since the brief's phrasing ("the icon catalogue... is the store to reuse") could also be read as "extend the icon catalog itself," which this design rejects. |
| Context | `chrona/render-context/v0.16` -> proposed v0.17 | Additive input (`inputs.containerImageCatalogs`), same shape and closure discipline as `inputs.iconCatalogs`. Context has bumped five times since v0.11 for additive inputs; this is ordinary, unlike View's contended version. |
| Layout | `layout/surface_composer.py` annotation box construction; `layout/balloon_geometry.py`; #466's `SurfaceObstacleIndex`/candidate search | The paint-box/content-box split is new but narrow: exactly one more derived rectangle (content box expanded by a declared inset) feeds the same collision and candidate-search code that already reasons about "the box." No change to search order, obstacle classes, or the #466 fallback/warning contract. A `rectangle`/`balloon` role with no `contentInsetEm` declared keeps content box == paint box, i.e. today's behavior, by construction (the inset defaults to zero when the outline is not `image`). |
| Scene | `scene/model.py` `ScenePaint`; `scene/v05_builder.py` Rect/Symbol projection for `annotation-box` | `ScenePaint.image` is additive and structurally parallel to the already-shipped `ScenePaint.gradient`. The container's Scene `kind` (`Rect` or `Symbol`) is unchanged by this design — an image outline does not introduce a third Scene primitive kind, so "one container mechanism" holds at every layer, not just at the Theme schema. |
| Contrast (#459) / Perceptibility (#446) | `scene/contrast_policy.py` `_ground_under`; `scene/perceptibility.py` `_occlusion_findings`, `_paint_findings` | Traced explicitly (design Contract 4): both modules pattern-match on `kind in {Rect, Symbol}` and `paint.fill`/`paint.gradient`; neither inspects `paint.image`. The declared `fill` becomes the ground for image-backed note text through the exact code path a plain rectangle uses today. This is the acceptance-bullet-3 requirement, met with zero lines changed in either module — the smallest contract available. |
| Adapters | Specification 64 §6 ("adapter... does not decide"); #466 "adapters do not invent a tail" | SVG embeds each tile with the same `b64encode` mechanism already used for raster icons (`renderers/v05_svg.py:182-184`), repeated per resolved tile; PNG stays derived from SVG via resvg. No adapter computes an inset, a tile boundary, or a stretch ratio. |

## Reviewed ambiguities and resolutions

1. **"The store to reuse" — pattern or resource kind?** The design chose
   "reuse the closure/identity engineering pattern, as a sibling resource
   kind" over "extend `chrona/icon-catalog/v0.3` itself." Reasoning: spec
   64 explicitly disclaims "arbitrary images/artwork" and reserves this as
   a separate family; folding container art into the icon catalog would let
   a View's ordinary `visuals` grammar reach it (contradicting acceptance
   bullet 1) and would stretch icon accessibility semantics (alternative
   text, decorative/meaningful) onto content that has neither. **This
   reading is not unanimous by construction — it is this review's
   judgment call, not a fact already settled in the codebase — so it is
   named to the lead/owner rather than silently finalized.** If the lead
   prefers the icon-catalog-extension reading, the affected documents are
   Specification 65 (would be withdrawn or narrowed to just the Theme
   binding grammar) and the D1 implementation slice (would target
   `chrona/icon-catalog/v0.3` instead of a new resource kind); nothing in
   Contracts 2–4 (Theme token, Layout geometry, Scene paint, adapters)
   changes either way.
2. **Asset provenance for the committed evidence asset.** The literal
   acceptance needs *an* image-backed container, not Yuya's actual scroll
   artwork. A repository-owned, non-photographic placeholder (a bordered
   nine-slice test panel) avoids a licensing decision in this slice; real
   target artwork is a named follow-up. Accepted as the minimal path; the
   lead may instead want to commission/approve real artwork before D5,
   which would only delay the evidence slice, not the mechanism slices
   D1–D4.
3. **Declared-vs-actual ground colour drift.** No code enforces that a
   Theme's declared `fill` matches the shipped artwork's actual content-
   area tone; a future import-time verification tool is named, not built.
   Accepted: acceptance bullet 3 asks that contrast/perceptibility *treat*
   the declared colour as ground, not that the system prove the artist's
   honesty. A wrong declaration is a Theme-authoring defect, structurally
   the same class of defect as today's `annotation.fill` not matching a
   designer's intent for a plain rectangle.
4. **Evidence slide sequencing against #466 C3/C4 and #467 L3.** Both are
   in flight against `02-programme-board`'s plot geometry. Building the new
   gallery slide now versus after those land is a scheduling choice, not an
   architecture one; the design plan recommends waiting (mirroring the
   #466 C3 sequencing correction's own precedent) but names the alternative
   plainly so the lead can choose based on actual timing, not this review's
   guess about it.

## Risks and gates

- **Corpus-count fixtures.** `tests/acceptance/output/test_public_geometry_regressions.py`'s
  hard-coded public-slide/primitive counts must be bumped by exactly the
  new gallery slide's own contribution, with the diff attributed in the
  slice review — not folded into an unrelated #466/#467 count change if
  those land first. Re-check the file's current counts immediately before
  D5, since #466 C3/C4 and #467 L3 may have already changed them.
- **Cross-session Theme/View file contention.** #466's own C3 sequencing
  correction records "uncommitted View and Theme edits, preserved as a
  patch by the lead" for `02-programme-board`'s Theme. #465's D2 (Theme
  schema) and D5 (gallery Theme) must not collide with that patch; the
  implementation plan should target a *new* Theme document (or a new role
  within the existing HALCYON Theme) rather than editing shared Theme
  files #466/#467 are actively changing.
- **Nine-slice degenerate geometry.** A paint box smaller than the declared
  fixed border (corner tiles overlapping) must not silently invert tile
  order or emit a negative-size destination rect; named as a required test
  in the design's own Tests section, not deferred.

No other unresolved architectural question remains; the one open decision
(ambiguity 1) is a scope/authority call for the lead or issue owner, not a
gap in this review's analysis.
