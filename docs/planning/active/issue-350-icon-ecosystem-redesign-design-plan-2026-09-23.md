# Design Plan: Icon Ecosystem Redesign (#350)

**Status:** Active — feedback reconciliation before implementation
**Issue:** #350 (reopened after post-hoc review)
**Supersedes as product scope:** the narrow local-asset assumptions of the
previous #350 plan and v0.1 delivery. The delivered closure/security foundation
remains evidence, not the completion claim for this issue.

## Objective

Deliver a reusable, offline, immutable icon ecosystem rather than a fixture-only
local-SVG mechanism. An author must be able to select a bundled icon by name,
ingest a supported local Iconify collection into an ordinary pinned catalog,
and attach catalog icons to supported presentation labels or marks with
instance-specific leading/trailing composition. The result must preserve the
existing authority chain:

```text
collection/catalog + Context closure + View selection + Theme treatment
  -> Layout placement and measured text -> completed Scene Icon -> adapter
```

No compatibility requirement protects the old catalog, Context, or View syntax
when a clean successor contract is necessary.

## Reconciliation inventory

Every feedback finding is an explicit design gate; none is silently deferred.

| ID | Verified gap in current v0.1 delivery | Required design outcome | Gate |
| --- | --- | --- | --- |
| R350-01 | Attribute-free path-only SVG accepts virtually no real ecosystem set. | A bounded source-normalization model accepts the declared monochrome Iconify subset, lowers supported elements/commands deterministically, and rejects unsupported artwork per icon. | D350R-1 |
| R350-02 | The vector model cannot preserve stroke-based artwork. | Per-path fill/stroke mode, width, cap, and join are normalized before Scene; literal colour, gradients, masks, images, and external references remain rejected. | D350R-1 |
| R350-03 | One optional Context catalog and dotted IDs cannot express independent sets. | A Context pins an ordered closed catalog set; references use canonical `set:name`, with declared aliases and deterministic ambiguity/absence diagnostics. | D350R-2 |
| R350-04 | No product default, set import, or package resource exists. | A local-only import tool consumes Iconify JSON, records collection/version/license/provenance, writes no partial catalog, and produces the packaged Material Symbols Outline Rounded default with `material:` and `material-symbols:` aliases. | D350R-2 |
| R350-05 | Schema admits object/annotation/group/mark but Layout implements objects only. | Every admitted source form has an implemented Layout projection or is removed from the successor schema; no valid declaration may become a dead Layout door. | D350R-3 |
| R350-06 | Icons attach only to an object label or mark. | The complete label vocabulary is enumerated as admitted or intentionally excluded, with source-owned per-instance selection and field-to-icon encoding where semantically valid. | D350R-3 |
| R350-07 | Placement is leading-only. | A label visual-slot contract permits at most one leading and one trailing visual, defaults to leading, reserves both before measurement/wrap, and records reading order. | D350R-3 |
| R350-08 | Size/gap are hard-coded and vertical alignment uses the line box. | Theme owns relative scale/gap tokens; Layout derives size from label typography and aligns to measured cap-height (or the named mark metric for marks). No absolute icon-pixel token is introduced. | D350R-3 |
| R350-09 | Label and mark share `iconMark`/`planned` paint, so leading icons do not inherit label colour. | A label visual inherits its owning label paint by default; a mark visual has its own semantic treatment. The semantic registry distinguishes these responsibilities without Theme choosing assets. | D350R-3 |
| R350-10 | Raster evidence is a shrunken full-slide screenshot. | Purpose-built bounded raster icon fixtures prove payload closure without treating arbitrary screenshots as icons; SVG/PNG output size and decoded visual evidence are bounded. | D350R-4 |
| R350-11 | Draft rendering has no catalog ingress and author-facing documentation is incomplete. | The draft command accepts explicitly named catalog resources; schemas, command help, diagnostics, examples, and annotations describe each author-facing successor field. | D350R-4 |
| R350-12 | Closure/release claims omitted requirements posted before closure. | A requirement-to-design-to-test matrix and release checklist make every accepted, rejected, or deferred requirement explicit in the issue and review. | D350R-5 |

## Design decisions to complete

### D350R-1 — Ingestion and normalized icon geometry

Specify an Iconify JSON collection ingestion boundary that reads only a supplied
local file. Define a versioned normalized catalog payload, finite limits,
deterministic shape/group lowering, and command normalization to the existing
renderer-neutral path vocabulary where possible. Establish and test a pinned
geometric tolerance if curve lowering is needed. Normalize only `currentColor`
and `none`; reject literal colours and all artwork features that would violate
Color Scheme authority. Decide whether an unsupported icon rejects the whole
collection (the default) and name the exact diagnostic with set/icon/element
provenance.

Review stroke carriage against Scene paint ownership and target profiles. It
must not let raw SVG styling or adapter-local interpretation pass the ingress
boundary. Validate the claimed practical compatibility using real Material
Symbols, Lucide, and Tabler corpus samples before choosing the final model.

### D350R-2 — Catalog topology, identity, provenance, and product default

Replace the one-catalog Context edge with an explicit ordered catalog set, each
independently revision/content-identity pinned. Define `set:name`, aliases,
duplicate/unknown set behavior, canonical catalog ordering, and the boundary
between bundled resources and user-owned imported resources. Define importer
input/output, atomic write behavior, provenance (source prefix/version/license
and notices), license-presence validation, and its deliberately local/no-network
operation. Verify the Material Symbols variant, licensing notice, names/aliases,
bundle size, and small-size rendering before making it the default.

The importer is an authoring/packaging tool only. It never runs during Context
resolution, materialization, Scene composition, or adapter serialization.

### D350R-3 — View selection and side-aware label composition

Define successor View and owning resource contracts for label visuals. Enumerate
all current text placements and record whether each is admitted, excluded, or
requires a source-contract extension: title, table column header, member label,
group header/detail, annotation/note, legend, summary header/metric/caption,
axis label, milestone digest, and mark. Define a shared visual-slot shape with
`ref`, logical `leading|trailing`, decorative/meaningful semantics, and one
visual maximum per side. Define source-specific per-instance selection plus a
closed `iconEncoding` for eligible object fields; unknown values reject.

Layout owns visual advance, cap-height alignment, text remeasurement/wrapping,
overflow, bidirectional reading order, and mark geometry. Theme owns
text-relative scale, gap, and resolved paint/finish; label visuals inherit the
label paint unless a distinct semantic mark role applies. Scene only projects
placements. Accessibility must preserve textual equivalents and apply meaningful
icon contrast requirements without using icons as sole meaning.

### D350R-4 — Public authoring, fixtures, and target evidence

Specify draft catalog inputs/CLI help and immutable Context catalog-set closure.
Replace the screenshot raster fixture with a small, purpose-specific source.
Create public evidence for bundled and user-imported catalogs, fill and stroke
icons, leading/trailing label positions, a selected mark, meaningful and
decorative accessibility, exact SVG/PNG profiles, and rejection-only targets.
Use decoded PNG/SVG assertions and bounded artifact-size checks; do not infer
fidelity from byte prefixes or unrepresentative source images.

### D350R-5 — Whole-architecture and release accountability

Amend Specifications 63/64 and only the owning Context/View/Theme/Scene seams.
Review interactions with Design Space, packages, Color Scheme, font metrics,
Layout, Scene, SVG/PNG/PDF/Typst/TikZ profiles, materialization, schema
inventory transition, and #349 diagnostics. Publish a matrix mapping R350-01
through R350-12 to design decisions, implementation slices, fixtures, and
acceptance evidence. Any rejected or future requirement must state why in the
issue and release review before closure.

## Planned publication sequence

| Phase | Published output | Completion condition |
| --- | --- | --- |
| P350R-1 | This reconciliation plan | all feedback inventory rows are recorded and #350 is open |
| P350R-2 | Design amendment plus architecture review | D350R-1 through D350R-5 resolve all rows, including real corpus evidence |
| P350R-3 | Successor implementation plan | independent reviewable slices, file ownership, migration/removal, and acceptance matrix are fixed |
| P350R-4 | Implementation slices | each slice is focused-tested, reviewed, and serially published |
| P350R-5 | Release review | full suite, conformance, materializers, artifacts, wheel smoke, CI, and issue matrix are all accepted |

## Non-goals retained unless a later design gate changes them

No arbitrary image/photo placement, raw SVG/CSS/XML at render time, network
fetch, renderer fallback/substitution, icon-only required meaning, literal
asset colours, PDF rich-paint claim, or unpinned package acquisition is
introduced. Multicolour logos/artwork stay outside this icon family and require
their own Image/asset design.

