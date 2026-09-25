# Current Evidence Disposition — Integrated Surface Quality Programme

**Scope:** #404, #403, #388, #389, #409, #405, #406, #407, #408, #400,
#414, #402, #413, #410, #412, #411.

**Evidence base:** `main` at `8a4f1e348795996d0d93c495db07b6a5686a4035`.

## Method

This review used the live View v0.15 and Layout Profile v0.4 schemas, the
current Layout/Scene/adapter source, and a fresh run of:

```console
./.venv/bin/python tools/presentation_coverage.py --root . \
  --output /tmp/presentation-coverage-current.md
```

The coverage run discovered 22 declared corpus slides. It is evidence of
declared vocabulary use, not proof that a visual distinction is painted. Each
row below therefore cites a structural source as well as corpus evidence.

## Disposition

| Issue | Current disposition | Evidence and resulting owner |
| --- | --- | --- |
| #404 | still-open | Spec 02 correctly distinguishes hierarchy from grouping, but View v0.15 still permits hierarchy grouping, Review-row depth, and WBS/path columns without an interaction contract. P1 owns the decision. |
| #403 | still-open | A v0.15 table column accepts `id`, `source`, `format`, and `missing`; `surface_composer` allocates natural widths only and indents index zero. P1 owns column intent and measured allocation. |
| #388 | still-open | `layout/presentation.py:place_rows` divides available timeline height uniformly by row count. P1 owns content-sized rows and declared surplus policy. |
| #389 | still-open | Scene carries completed rows but the adapter does not render row decoration; coverage shows no `grouping.presentation: band` corpus case. P1 owns cross-slot decoration. |
| #409 | still-open | Layout creates full-height `calendar-closed` rectangles and group bands; Scene paint order is builder order rather than a completed value. P1 owns background-channel and paint-order policy. |
| #405 | still-open | `surface_composer` uses the last configured level for labels/grid and first for bands. `ticks` remains a required View field without this mapping. P2 owns typed tier roles. |
| #406 | still-open | `fitting_axis` implements `auto` and `axis_intervals` implements `tick_step`, while corpus coverage finds no declaration exercising either. P2 owns public reachability. |
| #407 | still-open | Axis units remain day/week/month/quarter/year, and axis buckets are calendar-year based. P2 owns half-year/fiscal design; project-relative weeks require an explicit separate decision. |
| #408 | partly superseded, still-open | #401 closed the finite `en-US`/`ja-JP` locale contract, but one shared format enum still admits meaningless unit/format pairs. P2 owns per-tier label vocabulary and name-table separation. |
| #400 | still-open | `surface_composer` silently omits non-fitting axis labels and unconditionally raises on undersized uniform rows. P2 owns the taxonomy; P1 consumes it for row extent. |
| #414 | partly superseded, still-open | Its historical count includes #394/#395/#396/#397/#398/#399/#401, all now closed. The needed deliverable is a current semantic-to-visual realization report; P3 owns it. |
| #402 | still-open | projection assigns variance roles, while `v05_builder` emits every table cell through `tableCell`'s `text` role. P3 owns fact-to-cell role selection. |
| #413 | partly superseded, still-open | #393 fixed the `annotationText` binding and #394 supplies marker geometry. Annotation box/leader still share `annotation`, purpose is not independently styled, and leader routing uses relation policy. P3 owns the remaining semantic realization. |
| #410 | still-open | Typography and text measurement do not carry letter spacing, transform, numeric spacing, or orientation. P4 owns one measurement-and-paint contract. |
| #412 | still-open | all 22 corpus layouts use `horizontal-tb`; both vertical enum values remain unexercised and text has no orientation. P4 owns the explicit narrowing or semantics decision. |
| #411 | still-open | the raster registry passes `skip_system_fonts=True`; Context font providers remain reproducible inputs. P4 owns the draft-only provenance design decision. |

## Design constraints confirmed by the evidence

1. None of the remaining work belongs in SVG/PNG inference. Current defects
   arise before Scene or at a missing typed Scene value.
2. The post-#401 locale boundary stays finite. Label vocabulary must not turn
   into host locale behavior or arbitrary format strings.
3. The post-#394/#395 marker and relation contracts are dependencies of #413,
   not alternate mechanisms to recreate.
4. P1 must publish hierarchy rules before it changes column indentation,
   because the correct target column depends on the resolved hierarchy meaning.
5. P2 must publish visible/invisible failure classification before replacing
   either the row-overflow raise or silent axis-label omission.
6. P4 cannot add paint-only typography. A value that changes glyph extents must
   be supplied to measurement, placement, Scene, and every adapter together.

## Conclusion

The integrated programme plan remains valid. No listed issue is closed by
assumption; #408, #413, and #414 are narrowed to their surviving requirements,
and implementation may begin only after the corresponding English design and
cross-architecture review are published.
