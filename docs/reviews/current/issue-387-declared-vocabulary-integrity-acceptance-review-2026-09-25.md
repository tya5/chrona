# Acceptance Review: Declared Vocabulary Integrity (#387)

**Decision:** Accepted.

## Delivered contract

The repository now has a deterministic, checked declared-vocabulary inventory.
It compares every registered finite schema field to the acceptance boundary
owned by the product module, and records an explicit disposition for fields
that are intentionally open-ended.  The inventory is quality evidence only;
it is not a runtime policy authority.

The five identified schema-to-render divergences are closed at their owning
boundaries:

| Boundary | Accepted public contract | Result |
| --- | --- | --- |
| Theme marker/pattern/symbol | Theme v0.7 structured completed geometry | Schema and Theme/Scene ownership agree; adapters serialize completed geometry. |
| Render Context locale | `en-US`, `ja-JP` | Context validates the closed pair before Layout measurement. |
| View annotation anchor | required object/facet/endpoint form | View validates only the form Layout resolves. |

The former Theme v0.6 scalar-token migration was intentionally superseded by
#384 before this release gate.  The published correction at `23d3530c`
records that v0.7 is the acceptance basis; no v0.6 reader or live closure was
restored.  This preserves the accepted authority flow:

```text
schema/resource -> owning normalization -> Layout -> completed Scene -> adapter
repository inventory -> generated quality evidence only
```

## Evidence

| Gate | Evidence | Result |
| --- | --- | --- |
| Focused inventory and owner tests | `pytest -q tests/unit/tools/test_vocabulary_inventory.py tests/unit/chrona/presentation/model/test_surface_content.py tests/unit/chrona/presentation/layout/test_presentation_axis.py tests/unit/chrona/presentation/renderers/test_target_registry.py` | 42 passed |
| Generated inventory | `python tools/vocabulary_inventory.py --check` | Pass |
| Conformance | `python conformance/run_conformance.py` | Pass |
| Full suite and public materializer byte checks | `pytest -q`; every declared materializer check passed; `examples/` diff empty | Pass |
| Generated SVG review | No new generated-artifact diff after the completed v0.7 evidence accepted by #384 | Pass |
| Ubuntu, macOS, Windows | [GitHub Actions run 36031544094](https://github.com/tya5/chrona/actions/runs/36031544094) | Pass |

## Whole-architecture review

Theme, Context, and View remain the only owners of their respective authoring
vocabularies.  Layout retains measurement and geometry; Scene retains
completed primitive data; adapters neither choose Theme names nor accept
locales or View anchors.  No Core scheduling semantics, materializer
authority, or compatibility reader was added.  The v0.7 update therefore
strengthens the original #387 separation rather than creating another
registry or a renderer-side exception.
