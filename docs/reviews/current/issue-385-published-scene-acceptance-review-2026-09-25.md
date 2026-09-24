# Acceptance Review: Published Inspection Scene (#385)

**Decision:** Accepted, pending the required three-platform CI result.

## Scope reviewed

This review covers I385-0 through I385-3, including the two published design
corrections for raster icon viewport closure, Draft provenance, and the
release-gate reachability correction.  The latter removed the unreachable
historical `layout.lanes` helper rather than creating a false production path.

## Contract and ownership review

| Claim | Evidence | Result |
| --- | --- | --- |
| One completed runtime Scene is serialized | `InspectionScene` is produced by `render_review`; `scene-v0.1` is mapped only by the explicit serializer. | Pass |
| Layout owns geometry | Serializer, CLI, and adapter fixture import neither Layout composition nor renderer/Theme code; source-boundary test protects this. | Pass |
| Public document remains strict | The live schema has fixed object shapes and typed nested geometry, annotations for every authored node, and serializer cross-reference/finite checks. The rejected temporary generic-value form was not published. | Pass |
| Typed table contract | Surface columns and primitive row/column links are serialized explicitly and checked against declared rows/columns. | Pass |
| Asset closure | Raster icons contain immutable identity, viewport, alternative, and PNG encoding, never asset bytes or paths. | Pass |
| External consumer boundary | `tools/scene_adapter_fixture.py` is stdlib-only, imports no Chrona package, projects a capability-free corpus Scene, and rejects unsupported capabilities deterministically. | Pass |
| Stable evidence seam for #375 | Checked-in emitted Scenes carry `contentFamilyCounts` and `visualRoleCounts`; no SVG parsing or builder import is required. | Pass |

## Verification evidence

| Gate | Result |
| --- | --- |
| Focused Scene/schema/CLI/adapter/materializer tests | 126 passed |
| Focused live Layout checks after unreachable-helper removal | 34 passed |
| Full test suite on the final tree | 773 passed, 18 skipped, 0 failures, 0 errors |
| Schema annotations and all three representative Scene documents | Pass |
| Chrona conformance | Pass |
| Module reachability / dependency direction | 75 reachable, 0 staged, none orphaned / 9 packages, 33 inward edges |
| Diagnostic, declared-value, vocabulary, corpus coverage, gallery, and documented-command checks | Pass |
| Public materializer byte checks | All 20 declared corpus slides; Scene evidence for programme board, dependency network, and Controller Z icons also matched |
| Installed wheel smoke | Pass |
| Generated-artifact review | No unreviewed SVG or Scene diff remained; the three stale gallery comparison pages were regenerated from their current declared corpus inputs. |

## Architecture conclusion

The implementation adds a published inspection boundary without introducing a
second renderer, authoring protocol, layout engine, or plugin registry.  The
release-gate correction removes rather than stages an abandoned duplicate
lane policy, preserving `surface_composer` and `surface_quality` as the sole
live Layout owners.  #375 can now consume Scene evidence as designed.

## Remaining release condition

The local gate is complete.  Close #385 only after the GitHub Ubuntu, macOS,
and Windows workflow for this acceptance commit succeeds.
