# #350 Post-release Correction Release Review

**Decision:** accepted.  This review replaces the premature acceptance in
`issue-350-icon-ecosystem-release-review-2026-09-24.md`; that document remains
historical evidence of the rejected closure.

## Requirement and architecture review

All C350-1 through C350-5 design gates are accepted.  The architecture remains
strictly one-way: local Iconify collection -> normalized catalog -> closed
Context -> canonical View request -> Layout placement -> completed Scene paths
-> adapter.  Draft profile admission is explicit; package-resource materializing
rewrites only the immutable snapshot ingress, leaving render resolution on its
existing local reader.  No compatibility reader, renderer lookup, raw SVG, or
implicit profile upgrade was introduced.

The Material default records source package `@iconify-json/material-symbols`
version `1.2.93`, its exact source identity, 4,015 canonical entries, 4,757
aliases, and collision-checked short names.  The `@iconify/utils@3.1.7`
fixture covers all 8,772 names exposed by the bundled catalog; CI reads the
committed fixture and does not require Node.

## Reproducible evidence

- Focused correction suites: passed.
- Full parallel suite: `569 passed, 11 skipped, 38 warnings`.
- Schema annotation and View dispatch reachability gates: passed.
- `conformance/run_conformance.py`: passed.
- All 12 public materializers reproduced their committed SVG bytes: five
  Controller Z slides (including bundled Material title/header/exact-13px cell), one
  ASTER slide, and six HALCYON slides.
- Isolated wheel build/install smoke: passed; the wheel exposes the packaged
  Material catalog through `importlib.resources`.
- GitHub conformance CI: passed on commit `4a1ff83`
  (run `35932276143`, macOS).

The requirement matrix records direct evidence for R350-01 through R350-12.
