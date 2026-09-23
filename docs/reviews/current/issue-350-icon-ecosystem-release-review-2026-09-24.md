# #350 Icon Ecosystem Release Review

**Decision:** superseded — post-release review found red CI and unmet public
authoring/catalog requirements.  See the [post-release correction design
plan](../../planning/active/issue-350-post-release-correction-design-plan-2026-09-24.md)
and its architecture review.  This document is historical evidence only and
does not close #350.

The successor catalog, View-to-Layout composition, completed Scene path
boundary, public authoring path, and evidence matrix satisfy R350-01 through
R350-12. No compatibility reader or renderer fallback was retained.

## Release evidence

- Full suite: `554 passed, 10 skipped` on 2026-09-24.
- All 11 public materializers reproduced their committed SVG bytes: four
  Controller Z, one ASTER, and six HALCYON slides.
- Controller Z icon evidence covers vector/raster, direct/trailing/encoded
  selection, meaningful/decorative accessibility, bounded decoded PNG, and
  generated SVG size.
- Public local Lucide/Tabler fixture regenerates its v0.3 catalog byte-for-byte.
- SVG adapter imports no Layout, Theme, or normalizer policy; Scene projects
  completed icon paths only.

## Architecture review

Catalog ingress validates source bytes; Context closes assets; View selects
intent; Layout owns geometry; Scene completes paths and paint; adapters only
serialize. The requirement matrix records direct evidence for every R350 row.
