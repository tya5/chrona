# Release Review: Wheel Resource Topology and Evidence (#379, #381)

**Decision:** Accept, subject to the recorded three-platform CI publication
gate.

## Scope and published implementation

`11a0598` removes the copied `src/chrona/resources/examples/halcyon-1` tree
and its synchronization checker.  Hatch now force-includes the sole authored
`examples/halcyon-1` authority.  `chrona.resources.template_resource()` owns
the package/source selection and requires the `manifest.yaml` sentinel, while
local init consumes the resulting named `Traversable`.

`a336ba7` extends `tools/wheel_smoke.py` only through public CLI journeys:
`init` and `materialize` cover the template, schemas, and metric resources;
`icon-catalog material-default` copies and validates a non-empty icon catalog;
and Draft PNG rendering checks the PNG signature after the renderer resolves
the declared bundled font bytes.  The smoke therefore reaches every current
resource tree without direct resource reads or a checkout-path fallback.

## Acceptance evidence

| Requirement | Evidence | Result |
| --- | --- | --- |
| One authored init template | `pyproject.toml` force-includes `examples/halcyon-1`; the copied tree and `tools/check_init_template.py` are absent from tracked source. | Pass |
| Development authority is usable | `PYTHONPATH=src:.` `initialize_project()` created a project containing `manifest.yaml`. | Pass |
| Installed product is usable | A newly built wheel was force-installed, then `tools/wheel_smoke.py` ran from a fresh directory outside the checkout. | Pass |
| Every resource tree has public proof | Wheel smoke completed template initialization/materialization, catalog copy-and-contract validation, and Draft PNG signature validation. | Pass |
| Wheel contains intended assets | Wheel member inspection found forced-included template files plus bundled `resources/icons/` and `resources/fonts/` assets. | Pass |
| Init behavior retains its contract | Focused packaged-resource/local-authoring tests: 7 passed. | Pass |
| Existing materializer evidence is unchanged | Conformance and the public materializer integration test passed; working tree remained clean after generation checks. | Pass |
| Structural and full regression checks | Conformance, documented-command execution, reachability, Scene primitive delivery, View dispatch, import-direction, text-encoding, diagnostic/value inventories passed; `pytest -n 4 -q`: 728 passed, 17 skipped. | Pass |

## Architecture review

The completion preserves the accepted boundaries: the corpus remains the only
template authority; installation topology remains isolated in the resource
layer; init remains a use case rather than a path-discovery mechanism; and
wheel evidence remains a user-visible CLI test.  PNG smoke is intentionally
temporary Draft output, so it does not redefine immutable Context or public
materializer byte-evidence policy.  No Project, Context, Layout, Scene, or
materializer contract changed.

## Publication gate

Run the `conformance` workflow for the current `main` commit on Ubuntu, macOS,
and Windows.  On success, verify the commit and all matrix jobs in GitHub, then
close #379 and #381 with this review as their completion evidence.
