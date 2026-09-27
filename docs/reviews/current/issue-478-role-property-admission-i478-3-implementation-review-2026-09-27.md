# I478-3 Implementation Review — Theme Role/Property Admission

**Implementation:** `cf09ab1d39a4502c328ab7255e39da2ac7bb258f` on
`main`, via [PR #495](https://github.com/tya5/chrona/pull/495).
**Public base:** `504d3307d0521a621bc2067ae751e7b724f69abc`.
**Authority:** the [rebase design correction](../../design/issue-478-role-admission-rebase-correction-2026-09-27.md),
[axis amendment](../../design/issue-478-axis-typography-role-admission-amendment-2026-09-27.md),
[legend amendment](../../design/issue-478-legend-role-admission-amendment-2026-09-27.md),
[open-name overlap correction](../../design/issue-478-open-role-family-overlap-correction-2026-09-27.md),
their published architecture reviews, Specifications 07/33/39, and the
[implementation-plan amendment](../../planning/active/issue-478-role-admission-implementation-amendment-2026-09-27.md).
This is the I478-3 slice review, not the final I478-4 issue release review.

## Atomic migration and output evidence

- The product merge contains the finite role/property consumer projection,
  validation of every direct binding and Scheme target in effective Theme
  closure, 24 public Theme source updates (17 example roots including two
  derived pin updates, plus seven preset bundles), two focused test modules,
  refreshed diagnostic inventory, and 28 regenerated Scene files. No Theme
  syntax or selected visual profile changed.
- The authored Theme migration removed 55 direct role-property bindings:
  `annotation.strokeWidth` (22), `variance-behind.strokeWidth` (22), and
  `baseline.strokeWidth` (11). It removed 133 Scheme targets:
  `annotation.stroke` (22), `variance-behind.stroke` (22),
  `groupHeader.fill` (22), `asOf.stroke` (11), `axis.fill` (11),
  `baseline.stroke` (11), `heading.fill` (11), `legend.fill` (11),
  `summary.fill` (11), and `numeric.fill` (1). Consumed
  `dependency.marker`, annotation-box `annotationContainer`, axis inline
  visual ratios, and rich-profile `planned` shadow capability remain.
- All 24 Theme roots resolve with their declared Scheme, including both
  pinned derived Themes. The 28 manifest-declared public slides regenerated
  and passed `tools/regenerate_public_examples.py --check --jobs 4` in one
  batch. All 28 SVG files are byte-identical to the public base. There is
  no committed public PNG artifact; unchanged SVG bytes are the direct
  adapter-output comparison for the public SVG surface.
- Comparing every old and new parsed Scene after removing only Theme
  provenance and unsupported `stroke`/`strokeWidth` on Text roles yields
  exact equality for all 28 files. The 119 removed Text stroke payloads are
  `variance-behind` (88) and `annotation` (31). Neither SVG paint nor
  geometry, primitive identity, routing, or text placement changed.

## Verification and CI disposition

- Local project `.venv` includes the packaged Noto CJK provider. The related
  focused suite passed **146 tests** after restoring the Layout-consumed axis
  inline-visual ratios; the focused admission/closure tests passed again
  after the final portable-decoding correction. Local
  `conformance/run_conformance.py`, `tools/diagnostic_inventory.py --check`,
  public-materializer `--check --jobs 4`, and `git diff --check` passed.
- [Initial PR CI run 36283680325](https://github.com/tya5/chrona/actions/runs/36283680325)
  passed newest-Python public reproduction but failed conformance on all
  three OSes because the generated diagnostic inventory lacked the new
  error sites. Windows also found one new test reading UTF-8 Scene JSON
  with its default charmap. These were introduced by this slice, not
  independent failures. Commit `e487ae37` regenerated the inventory and
  specified UTF-8 explicitly; neither change altered product rendering.
- [Replacement PR CI run 36284194731](https://github.com/tya5/chrona/actions/runs/36284194731)
  passed all four jobs: Ubuntu, macOS, and Windows conformance/full pytest/
  wheel-smoke, plus newest-Python public-materializer reproduction. PR #495
  then squash-merged cleanly to `cf09ab1d`.
  [Post-merge `main` run 36284398114](https://github.com/tya5/chrona/actions/runs/36284398114)
  independently passed the same four-job gate at the actual public commit.

## Architecture conclusion

The validator runs at the effective Theme/Scheme closure boundary before
Layout and Scene. It checks both declaration sources separately so an
overwriting Scheme binding cannot hide an invalid direct declaration, and
preserves `/body/roles/<role>/<property>` versus
`/body/colorBindings/<target>` pointers through Draft, immutable, and
derived Theme closure. The contract records known Theme roles, actual Scene
kind consumers and per-property ownership. The bounded open-name axis
measurement and fixed-square legend paint producers overlap only for an
otherwise unregistered name; the registered `group:<stable-key>` colour
family remains fill-only. Known Text/Icon/Path roles keep narrower rules.
Layout geometry, Scene paint completion, and adapter serialization retain
their published boundaries. The public output diff confirms that no
supported visible treatment was removed.

## Literal Issue #478 criterion disposition after I478-3

| # | Literal acceptance criterion | State | Direct evidence / next unit |
| ---: | --- | --- | --- |
| 1 | Rendering `elevated-light` under the default profile emits a diagnostic that names the dropped treatment and the profile that would paint it. | met | [I478-2 review](issue-478-declared-treatment-visibility-i478-2-review-2026-09-26.md) and passing replacement CI; no I478-3 policy change. |
| 2 | A Theme property on a role that cannot carry it is diagnosed at load time. | met | Direct and Scheme pointer tests, Draft/immutable/derived closure tests, finite consumer sweep, 24-Theme migration and four-job CI above. |
| 3 | Suppressed plot labels are counted in an info diagnostic, or the View can ask for a visible marker on rows whose label was suppressed. | met | [I478-1 review](issue-478-declared-treatment-visibility-i478-1-review-2026-09-26.md) and passing replacement CI; no I478-3 label-policy change. |

I478-3 is accepted at `cf09ab1d`. Issue #478 remains open until I478-4
rechecks the complete public behavior and publishes its final acceptance
review; this slice review alone does not authorize closure.
