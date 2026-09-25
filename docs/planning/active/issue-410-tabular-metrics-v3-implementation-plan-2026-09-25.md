# Implementation Plan — #410 I410-2 Tabular Metrics v3

**Design:** `e6e40ede`; **architecture review:** `0fd9c656`.

## Atomic implementation unit

I410-2 is one migration commit.  No intermediate state may dispatch a Context
that refers to an unavailable metric algorithm, or materialize a public signed
numeric table with an unmeasured feature.

### 1. Metric v3 resource closure

* Extend font import to extract pnum/tnum digit glyph advances and write
  `chrona/font-metrics/v3` with both complete maps.
* Extend `FontMetrics` and resolution validation; its width API selects the
  already-resolved numeric mode and rejects invalid/missing v3 data.
* Generate new pinned packaged Noto Sans regular/bold metric files and update
  the packaged default descriptor to `declared-metrics-v3`.
* Add unit fixtures for default-tabular/pnum-proportional, missing digit,
  nonuniform tabular, invalid source identity, and import output.

### 2. Context v0.16 and public resource migration

* Create `render-context-v0.16` requiring `declared-metrics-v3`; move resource
  dispatch and schema inventory to it with no v0.15 reader.
* Migrate every public Context, conformance fixture, draft constructor, and
  contract test to v0.16/v3 and new package metric identities.
* Keep old schema/data files only as historical transitioning artifacts; no
  live resource may reference them.

### 3. Semantic numeric table measurement

* Add `typography_role` to normalized table cells; select `numeric` only for
  `signedDays` and retain `text` for headers/other cells.
* Generalize table allocation to receive a Layout measurement callback and
  thread each cell's complete treatment through natural size, ellipsis, and
  end alignment.
* Add the tabular `numeric` role to every HALCYON Theme used by a signed-day
  public View.  Do not add a View font-feature field or Scene-side branch.

### 4. Completed projection and evidence

* Make target serializers emit the supplied proportional/tabular selection;
  add direct SVG/Typst/TikZ tests with no font-resource imports.
* Regenerate every affected public Context/Scene/SVG evidence and inspect
  intended geometry/output changes, including HALCYON signed-day columns.
* Regenerate diagnostic and vocabulary inventories if their source locations
  or vocabulary change.

## Acceptance gates

1. focused metric/importer/resolver, table measurement, contract, Scene, and
   target-adapter tests pass;
2. all public materializers reproduce regenerated evidence and a HALCYON
   signed-days column is right aligned with tabular Scene/SVG evidence;
3. `pytest -q -n 4`, conformance, schema/delivery/import-direction checks, and
   package smoke pass;
4. generated SVG/Scene diffs contain only declared Context/metric/provenance
   and numeric-treatment effects;
5. publish an English acceptance review, push serially after remote-main
   verification, then proceed to I412-1/I411-1.
