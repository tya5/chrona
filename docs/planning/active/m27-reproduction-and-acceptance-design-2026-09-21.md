# M27 Reproduction and Acceptance Design — 2026-09-21

**Status:** D27-4 design complete; implementation is not authorized by this document.

## 1. Materializer contract

`tools/materialize_example.py` is the planned generic delivery tool. Given one v0.5
example `manifest.yaml`, a slide ID, and an output directory, it MUST:

1. read only the manifest-declared raw Context resource and snapshot directory, then
   derive its exact immutable reference;
2. materialize their canonical bytes into a temporary local immutable Revision Store;
3. construct resource references with exact content identities and a Render Context;
4. invoke the public `chrona render-review` CLI; and
5. write only the requested derived SVG and a normalized closure manifest.

It MUST NOT use Git `HEAD`, a working-tree input as a semantic selector, host fonts,
direct internal Scene imports, example-ID branches, or a serializer other than the
public CLI route. A missing manifest resource, stale identity, unknown slide, or
non-empty protected output directory is a deterministic failure.

The manifest continues to be authoring input; the generated context, Store, closure
manifest, SVG, and optional preview are derived artifacts. The materializer does not
grant examples an independent resource model.

## 2. Artifact policy

Each declared slide has exactly one expected SVG target. `--check` materializes into a
temporary directory and compares canonical bytes with that target. `--write` is an
explicit maintenance operation that replaces only a declared target after all semantic
tests pass; it cannot rewrite sources, create undeclared slides, or update a Context
identity without the source resource change that causes it.

Byte identity is required because input closure, ordering, numeric precision, font
metrics, locale, and SVG serialization are all explicit. A semantic assertion suite
supplements byte identity so deliberate, reviewed artifact regeneration cannot hide a
lost primitive family.

## 3. Acceptance matrix

| ID | Scenario | Required automated proof |
|---|---|---|
| A27-01 | Complete declared review surface | One generic and one existing example produce required heading/subtitle, role typography, table, calendar axis, groups, marks, legend, annotations, and summary/detail families. |
| A27-02 | Table missing policy (#31) | `blank`, `em-dash`, and `unknown` emit their normalized values, never enum names. |
| A27-03 | Axis policy (#30) | Calendar month/quarter intervals follow the View window; measured required labels do not overlap or cross their resolved slot boundary. |
| A27-04 | Actual distinctions | Planned, Actual, milestone, ahead/on-track/behind variance, missing Actual pattern/text, and unmatched Actual retain separate purpose/facet/role evidence. |
| A27-05 | Groups and routing | Declared group surfaces/headers/row shading and finite dependency/leader routes serialize with provenance and declared markers. |
| A27-06 | No empty reserved slot | Every present slot family emits the resolved family or raises the specified incomplete/overflow diagnostic. |
| A27-07 | Reproduction (#29) | Materializer `--check` is byte-identical for every declared example slide and detects a changed expected SVG. |
| A27-08 | No reduced fallback | A test instruments the public CLI route and rejects `ReviewScene`/`table_timeline` reachability. |
| A27-09 | Resource isolation | Changing Color Scheme changes only resolved colors; malformed/missing resolved Detail/Layout/Theme input fails before SVG. |
| A27-10 | Release regression | Full pytest, all existing conformance runners, M27 conformance fixture, and generated-example checks pass in CI. |

## 4. CI boundary

The M27 CI job first runs schema/fixture validation, then unit/integration/CLI tests,
then `materialize_example.py --check` for all manifests, and finally conformance. It
does not use a snapshot of a locally generated output as input to a later assertion.
Failure output names the manifest, slide, input closure identity, and first differing
artifact byte or missing semantic family.

## 5. Issue closure evidence

- #31 closes only with A27-02.
- #30 closes only with A27-03.
- #29 closes only with A27-06 through A27-08.
- #33 closes only after A27-01 through A27-10.
- #28 closes as obsolete only after the existing v0.5 context test and A27-07 are both
  green; it is not reopened as a separate implementation scope.
