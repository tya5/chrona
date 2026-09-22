# Source architecture

How `src/chrona` is arranged, which way its dependencies point, and where a new
capability goes. Two lints enforce the shape described here; this page explains
why it is that shape.

## Layers

Dependencies point inward. A package may import only the packages listed for it
in the table inside [`tools/check_import_direction.py`](../../tools/check_import_direction.py),
and no two packages may import each other.

| Layer | Packages | May depend on |
|---|---|---|
| Adapters | `app` | use cases, and the ports it wires |
| Use cases | `usecases`, `operational` | everything below |
| Services | `presentation`, `scheduling`, `storage`, `extensions`, `commands`, `release`, `collaboration` | the shared kernel |
| Shared kernel | `core`, `resources` | nothing but packaged schemas |

A **use case** owns one pipeline end to end and knows nothing about how it was
invoked: it reads no arguments, writes no files and prints nothing. It takes
resolved inputs and returns a result or raises a typed error.
`usecases/render_review.py` is the reference: an adapter hands it a closure, it
returns the SVG, the Scene surface, and the set of closure inputs the render
read.

A **port** is the narrow view an inner layer needs of an outer one, declared in
`core/ports.py`. `SnapshotReader` is one method; `storage` supplies the adapter
behind it. This is why `extensions` and `presentation` can read pinned
resources without depending on the store.

## The render pipeline

One order, owned by `usecases/render_review.py`:

```
closure → schedule → projection → content → measure → layout → scene → render
```

- **closure** (`presentation/model/closure.py`) resolves and verifies every
  declared input against its exact schema and, when pinned, its content identity;
  it then exposes only frozen typed contracts to the use case.
- **schedule** (`scheduling/`) places the Project; a bound Snapshot is scheduled
  the same way.
- **projection** (`presentation/model/projection.py`) selects, groups and orders
  rows and produces the first typed record, `ReviewProjection`.
- **content** (`presentation/review/v05_content.py`) turns Project, View and
  profiles into `SurfaceContentInput`: what the surface says, with no geometry.
- **measure / layout** (`presentation/layout/`) owns *all* geometry, in
  `Decimal`. Nothing downstream measures text or moves a box.
- **scene** (`presentation/scene/`) maps placed geometry to `ScenePrimitive`,
  choosing a semantic for each; it computes no positions.
- **render** (`presentation/renderers/`) maps primitives to an output format and
  makes no layout decision. The use case depends on the `Renderer` port, not a
  concrete serializer.

Each stage consumes the previous stage's result and nothing else. Text is
measured once, in Layout, with the font metrics the closure pinned. `Scheduler`
and `Renderer` are behavioral ports in `core/ports.py`; the CLI wires their
reference adapters and never selects an algorithm.

## The three registries

Each concern is declared in exactly one place, and a test fails if something
else declares it.

- **`presentation/model/semantic_registry.py`** — every visual meaning the
  surface can carry, with the Scene purpose, Scene role and Theme role it
  resolves to; plus `Slot` (what a Layout Profile may bind content to) and
  `PrimitiveKind` (what a renderer must draw). Adding a visual idea is one entry
  plus the code that draws it.
- **`schemas/`** — one JSON Schema per contract kind. A contract is validated at
  the closure boundary, not where it is read.
- **`core/diagnostics.py`** — the shape of a failure: a stable `E_*` identifier,
  a message and a pointer. Every layer reports through it rather than raising a
  bare exception message. The identifiers themselves are owned by the
  specification that defines each contract.

## Determinism and identity

Every input is addressed by store, address and immutable revision, and may pin
a content identity; a supplied pin is verified, an absent one is allowed
([ADR-0030](../decisions/ADR-0030-materializer-opt-in-content-identity.md)).
The same closure renders byte-identical output on any machine, which is what
`tests/integration/test_materialize_example.py` and the committed
`examples/*/generated/*.svg` assert.

Because that assertion compares bytes, it cannot tell a correct rendering from
the last one produced. `tests/acceptance/output/` therefore asserts *properties*
of the document — no text over a mark, nothing outside the viewport, every
declared slot draws something, every closure input is read — with the failures
that exist today pinned in `known_failures.yaml` and `known_unused.yaml`.

## Adding something

| Addition | Where |
|---|---|
| A visual meaning | one entry in `semantic_registry`, plus the draw path |
| A surface region | a `Slot` member, the Layout Profile schema enum, and a composer function |
| An output format | a renderer under `presentation/renderers/`, selected by the Context target |
| A contract field | its exact JSON Schema, frozen contract, then the one module that reads it |
| A pipeline | a module under `usecases/`, explicit ports, and a thin handler in `app/cli.py` |

## Checks

| Check | Enforces |
|---|---|
| `tools/check_import_direction.py` | the layer table above, and no cycles |
| `tools/check_module_reachability.py` | every module is reachable from an entry point or listed in `tools/staged_modules.txt` with a reason |
| `conformance/run_conformance.py` | the published contracts against their fixtures |
| `tests/acceptance/output/` | properties of the rendered document, and that the vocabularies agree |
| `tests/integration/test_materialize_example.py` | byte reproduction of every example |

All of them run in CI on every push and pull request.
