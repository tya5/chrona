# Issue #355 — Corpus Coverage Design

**Decision:** Accepted

## Scope

This design completes the policy half of #355 after PR #356 established four
semantic-register corpus projects.  It introduces a maintainer-owned,
deterministic coverage report.  The report describes public examples; it has no
runtime import path and cannot reject a user Project or alter materialization.

## Data model

The report has two intentionally distinct inventories.

1. **Contract registers** are explicit, stable feature probes for the Project,
   Actual, Snapshot, and Extension contracts.  A probe has an identifier,
   owning contract, a source path expression, and a predicate over a decoded
   declared corpus resource.  A probe is shown as exercised by every project
   whose declared resource satisfies it.
2. **Schema vocabulary** is a structural, non-normative inventory of finite
   `enum`/`const` values found in the four owning schemas.  It records values
   exercised by decoded corpus resources where a direct path is meaningful and
   reports all others as uncovered.  It does not infer semantics from prose or
   claim that every open object map is enumerable.

This split avoids a misleading promise that arbitrary JSON Schema structure can
be mechanically proved exercised.  Contract-register probes provide the stable
curation claims; schema vocabulary reveals bounded backlog.

## Inputs and output

`tools/corpus_coverage.py --root . --output docs/examples/corpus-coverage.md`
reads only:

- `examples/*/manifest.yaml` to discover declared regression corpora;
- each project's `project.yaml`, optional `actual.yaml`, declared snapshot
  resources, and declared extension package resources; and
- the four source schemas under `schemas/`.

It writes canonical UTF-8 Markdown with lexical project/probe/value order,
fixed headings, repository-relative paths, and no timestamps.  Atomic output
prevents a partial report.  `--check` compares generated content with its
existing output and emits a stable stale-report diagnostic; it is available to
maintainers but deliberately is not added to required CI gates.

The report contains: register table; Project/Actual/Snapshot/Extension probe
matrix; finite-schema vocabulary matrix; and explicit uncovered rows.  Every
positive cell links to the resource path that supplied evidence.

## Ownership and boundaries

```text
declared corpus resources + source schemas
             -> corpus_coverage (maintainer tool)
             -> docs/examples/corpus-coverage.md
             -> gallery curation backlog
```

The gallery generator may display the committed report or invoke the same pure
report model; it may not reinterpret corpus documents.  Presentation modules,
the public CLI, materializer, Layout, Scene, and adapters never import this
tool.  The policy guide owns selection rules; Specification 32 continues to
own example topology.

## Register probes

The first release fixes the following probes so output changes are reviewable:

| Contract | Probe | Evidence predicate |
| --- | --- | --- |
| Project | `deadline` | any object deadline |
| Project | `constraints` | any start/end constraint |
| Project | `negative-lag` | relation lag begins with `-` |
| Project | `hierarchy` | group parent or WBS code |
| Project | `scenario-relation-edit` | scenario removes or adds a relation |
| Actual | `point-observation` | record has `actual.at` |
| Actual | `in-flight-observation` | record has start/progress without finish |
| Actual | `progress` | record has progress |
| Snapshot | `pinned-snapshot` | declared snapshot-ref plus captured project |
| Extension | `declared-profile-package` | Project extension refers to a declared package |
| Extension | `typed-field` | profile package declares field definitions |

New public contract fields add a probe and an exhibiting corpus resource in the
same release.  A missing probe is a review finding, not a silent heuristic.

## Acceptance and test strategy

- Unit tests prove report byte determinism, lexical ordering, `--check`, and
  each register predicate using minimal decoded resources.
- Integration tests run the tool over the repository and assert all four
  registers plus their declared evidence paths appear.
- A negative fixture proves undeclared snapshots/extensions do not count.
- Full pytest, existing conformance/structural gates, all declared materializer
  reproductions, installed-wheel smoke, generated SVG review, and GitHub CI
  remain the release boundary.  Report coverage itself is not a threshold.

## Whole-architecture review

The design agrees with #348: gallery/corpus documentation is downstream-only
and cannot become an alternate closure.  It agrees with the repository layout:
schemas remain the source authority, examples remain the evidence authority,
and generated documentation belongs under `docs/`.  It introduces no resource
kind, renderer feature, package acquisition edge, compatibility reader, or
network access.
