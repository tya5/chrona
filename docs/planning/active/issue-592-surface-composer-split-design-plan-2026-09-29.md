# Issue #592 — surface composer split work record

## Published baseline and design plan

Public base: `a7358bcb72ad72a96cc600f09f3e5cb8dcf22981`. [Issue #592](https://github.com/tya5/chrona/issues/592) is open without comments; [board #454](https://github.com/tya5/chrona/issues/454) places it in P0 before parallel #582–#588 work. The issue cites 3,457 lines; `surface_composer.py` has 3,403 lines on this base. Published Spec 33 gives Layout authority over completed geometry, measurement and routing. `tools/check_module_reachability.py` is registered in conformance; new modules must remain reachable. The composer has nested closures sharing placements, metrics, obstacle state, diagnostics and output order. Exact phase read/write sets and public byte baseline remain unverified; no product change is authorized by this plan.

### Literal issue acceptance

- [ ] `surface_composer.py` contains orchestration only, under about 400 lines. Each concern module has a docstring naming what it owns and what it reads.
- [ ] Every public materializer and Scene is byte-identical, and the full test suite passes unchanged.
- [ ] The module reachability gate covers the new modules.
- [ ] Ownership notes are added to spec 33 (Layout ownership), so future issues can name the module they touch.

### Design questions and architecture boundary

1. Map the existing call graph, nested closures, mutation order and read/write sets. Confirm dependency edges among table/columns, axis, group bands/headers, marks, member labels, lanes, annotations, legend and routes; do not turn shared mutable state into a long argument list or duplicate authority.
2. Select typed phase inputs/results for placements, obstacle registrations, diagnostics and stable identity while preserving byte order. Keep `surface_composer.py` as the ordered coordinator; each concern module states what it owns and reads. Verify no import cycle or View/Theme/Scene responsibility leak.
3. Review the module map against all of Spec 33, source architecture, import-direction rules, adjacent lane/annotation/mark designs and #590's generated-evidence workflow. Add concise ownership notes to Spec 33 without making private module paths into new public semantics.
4. Define a complete byte-identity baseline for all manifest-listed public SVG and Scene outputs, plus focused semantic fixtures. A no-behavior-change split has zero intended generated diff; run focused tests at each extraction and full CI at final acceptance. Check module reachability and import direction after each slice.

### Review and publication slices

| Slice | Publishable result | Evidence |
| --- | --- | --- |
| D1 design | Confirm concern dependency map, typed result contract, orchestration order and whole-architecture review in this record; update Spec 33 ownership notes. | Source-grounded call/read/write map and no semantic/schema migration. Publish before implementation planning. |
| P1 implementation plan | Sequence extraction by dependency in independent reviewable slices; name files, type changes, focused tests, byte baselines, and publication units. | Complete 29-materializer SVG/Scene inventory, reachability/import gates, full CI release gate. Publish before product code. |
| I1…In extraction | Move one coherent concern at a time; preserve composer function and public bytes after each publication. | Focused tests, complete byte comparison, module gate, generated diff = none. |
| A1 acceptance | One literal review, exact review-bearing `main` CI, issue closure and archive. | All four criteria verified directly. |

The next step is D1; #582–#588 do not run in parallel until #592 completes. #590 and #591 remain separate P0 contracts and must not be solved by this structural split.
