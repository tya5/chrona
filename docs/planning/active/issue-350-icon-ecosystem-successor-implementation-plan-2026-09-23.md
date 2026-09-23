# Implementation Plan: Icon Ecosystem Successor (#350)

**Status:** Active — implements Specification 64 v0.2
**Design authority:** Specification 64, corpus evidence, and the #350 icon
ecosystem architecture review dated 2026-09-23.
**Compatibility:** not retained. The v0.1 icon contracts and fixtures are
removed in the first completed migration slice.

## Requirement allocation

| Requirement | Slice(s) | Direct acceptance evidence |
| --- | --- | --- |
| R350-01 normal real-set geometry | I350R-2 | Material/Lucide/Tabler fixture imports and bounded normalized output |
| R350-02 stroke model | I350R-2, I350R-5 | fill/stroke path serialization and no raw SVG adapter input |
| R350-03 catalog set + `set:name` | I350R-1, I350R-3 | duplicate/unknown alias negatives and multi-catalog Context closure |
| R350-04 importer/default/provenance | I350R-2, I350R-3 | local atomic import, license notice, packaged Material catalog |
| R350-05 no schema dead doors | I350R-1, I350R-4 | every target source schema test reaches Layout or is absent |
| R350-06 all labels + encoding | I350R-4 | target inventory fixture and direct/encoded selection checks |
| R350-07 both sides | I350R-4 | leading/trailing reservation, wrap/overflow, visual-order evidence |
| R350-08 relative cap alignment | I350R-1, I350R-4 | v0.2 cap-height fixture, typography-relative geometry tests |
| R350-09 label/mark paint separation | I350R-4, I350R-5 | different completed paints for label visual and mark visual |
| R350-10 bounded raster evidence | I350R-3, I350R-6 | purpose-built PNG, decoded check, artifact-size limit |
| R350-11 draft ingress/docs | I350R-3, I350R-6 | repeatable CLI catalog input, help/schema annotation checks |
| R350-12 accountable closure | I350R-6, I350R-7 | published matrix, release review, issue disposition |

## I350R-1 — Successor contracts and migration removal

Create `icon-catalog/v0.2`, `render-context/v0.11`, `view/v0.12`, and
font-metrics v0.2 contracts. Replace one catalog reference with a catalog set,
replace dotted icon IDs with `set:name`, introduce typed visual targets/direct
reference/field encoding, and require exact cap height. Update typed resource
models, schema inventory, Context closure model, all examples/conformance, and
package resources in one atomic migration. Remove v0.1 catalog, v0.10 Context,
v0.11 View, and v0.1 font metric readers/schemas/fixtures rather than retaining
bridges.

**Files:** schemas/resources inventory, contracts, closure, font metrics,
example contexts/views/themes, conformance and schema tests.

**Acceptance:** no live predecessor parses; each successor field has a schema
description; catalog set ambiguity and every invalid target/encoding reject;
every former source kind is either a typed projected target or absent; cap
height is validated/identity-closed.

## I350R-2 — Deterministic local Iconify importer and vector normalization

Build the `chrona icon-catalog import` authoring command. Implement a bounded
Iconify JSON reader, SVG fragment/parser lowering, fixed transform handling,
shape lowering, arc/cubic-to-quadratic conversion under a pinned tolerance, and
per-path fill/stroke normalization. Emit a canonical v0.2 YAML catalog with
source identity/license/notice; write it atomically only after complete success.

**Files:** icon ingestion package, command parser/application adapter, catalog
serializer, source/corpus fixtures, normalizer/import tests.

**Acceptance:** actual Material Symbols, Lucide, and Tabler sample fixtures
import deterministically; unsupported XML/artwork/colour/limit cases fail with
set/name/path diagnostics; no source SVG/XML reaches Context, Layout, Scene, or
adapter; no importer performs network I/O.

## I350R-3 — Catalog-set closure, bundled default, raster, and Draft ingress

Resolve catalog sets into an immutable lookup, validate prefixes/aliases and
catalog/raster identities, close only verified bytes, and materialize exact
documents/assets. Generate and package the Material Symbols Outline Rounded
default through I350R-2, with required licence notice, aliases, fixed subset
manifest, and size limit. Replace the screenshot raster fixture with a small
purpose-built asset. Add repeatable draft catalog arguments and guided-workspace
equivalent explicit declaration.

**Files:** closure/materializer, package resources, CLI/draft/workspace ingress,
Controller Z/public examples, catalog/closure/materializer/CLI tests.

**Acceptance:** multiple pinned catalogs resolve `set:name` deterministically;
packaged and user-owned catalogs work offline; no catalog means icon use rejects;
asset tamper/path/alias/notice errors are exact; draft and immutable routes share
one closure; raster decoded dimensions/payload and generated artifact size are
bounded.

## I350R-4 — Complete visual target inventory and Layout composition

Implement every v0.12 label/mark visual target as one side-aware Layout path.
Add target resolution for title, columns, object labels, groups, annotations,
notes, legends, summaries, milestones, axis/as-of labels, and marks; implement
direct references and field encodings where declared. Compute leading/trailing
advance from typography ratios and cap-height. Re-measure all affected text,
preserve overflow policy, and record visual reading order/provenance. Separate
label-inherited and semantic-mark roles.

**Files:** View projection/content, Layout request/placements/text composition,
semantic registry, Theme token resolution, Scene input structural tests.

**Acceptance:** one target-inventory fixture exercises every admitted label
class and mark; changing width/side/typography changes only Layout placement;
unknown encoding, missing source, duplicate side, no cap height, and insufficient
space diagnose; Scene never measures, looks up, or chooses icon placement.

## I350R-5 — Completed Scene Icon and exact SVG/PNG serialization

Replace v0.1 icon primitive data with normalized per-path payload plus completed
paint/stroke scale/visual order. Project Layout placements only. Serialize fill
and stroke paths and closed PNG data in SVG; characterize resvg PNG from the
public route. Retain exact v0.7 SVG/PNG admission and explicit PDF/Typst/TikZ
rejection. Add accessible decorative/meaningful behavior and contrast checks.

**Files:** Scene model/projection/validator, visual capability policy, SVG/PNG
renderers, target and accessibility tests.

**Acceptance:** adapters import no Theme, catalog, raw normalizer, metric, or
Layout policy; label icon paint equals label paint while mark paint is distinct;
fill/stroke/PNG render visibly and deterministically; unsupported targets reject
before output.

## I350R-6 — Public evidence, authoring documentation, and generated audit

Publish reusable examples for bundled Material, user-imported Lucide/Tabler,
leading/trailing label slots, encoding, all target classes, meaningful/decorative
icons, and purpose-built raster. Regenerate only intended public output. Add
schema annotation lint, CLI help, source/closure artifacts, SVG semantics,
decoded PNG comparisons, and artifact size checks. Publish the R350 matrix with
links to each fixture/test.

**Acceptance:** users can follow a documented YAML/CLI path without hand-editing
raw SVG; all generated changes are explained; no obsolete v0.1 catalog assets
or screenshot fixture remains.

## I350R-7 — Release gate and issue closure

Run focused suites by slice, full parallel pytest, conformance, structural
checks, public materializer reproduction, generated SVG/PNG audit, isolated
wheel smoke, and Ubuntu/macOS CI. Conduct an architecture/requirement review of
the final diff, confirm each R350 row against direct evidence, record any true
future work explicitly, and only then close #350.

## Publication discipline

Each I350R slice is committed, reviewed, and pushed serially after remote-main
fast-forward verification. A discovered missing target, ownership violation,
unproven corpus normalization, profile mismatch, or fixture-quality defect
returns to Specification 64 and architecture review before implementation
continues.

