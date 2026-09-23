# Design Plan: Portable Icon Catalogs and Immutable Visual Assets (#350)

**Status:** Active — design in progress
**Issue:** #350
**Depends on:** Specifications 08, 13, 33, 50, 55, 62, and 63

## Objective

Give a Chrona author a reproducible, safe way to use named vector and raster
icons both as semantic marks and as leading elements of measured labels.  The
feature must accept locally authored SVG and PNG files through a versioned
catalog resource, close their exact bytes into materialized evidence, and
project completed icon geometry without allowing renderer syntax or a local
filesystem to become runtime authority.

## Verified starting point

- The current evaluation closure has typed YAML resource documents and a
  packaged-font exception, but no general visual-asset closure.
- Layout owns all text measurement, baselines, label coordinates, marks, ports,
  and routes.  Scene only projects completed placements; adapters serialize
  completed Scene primitives.
- The closed current Scene geometry contains Rect, Symbol, Path, and Text.
  `Symbol` is a diamond-specific semantic primitive and the SVG adapter accepts
  only its diamond form; the current Path-marker support is likewise triangle
  specific. Neither is an icon abstraction.
- The exact visual profiles introduced by #349 admit rich paint only for SVG
  and PNG. PDF, Typst, and TikZ remain baseline-only and must reject required
  capabilities before serialization.
- Specification 63 intentionally defers generic Image and raw target syntax;
  Specification 62 defers package acquisition. Neither may be bypassed by an
  icon feature.

## Admission boundary

The initial feature admits one new `icon-catalog` resource and two immutable
asset classes:

| Class | Authoring source | Closed Scene representation | Initial targets |
| --- | --- | --- | --- |
| `vector` | local SVG file | normalized bounded vector paths and paint-free viewport | SVG, PNG |
| `raster` | local PNG file | immutable image identity, intrinsic size, and completed bounds | SVG, PNG |

The catalog declares stable entry IDs, kind, source address, SHA-256 content
identity, intrinsic viewport, and accessible alternative. SVG is parsed and
normalized at the ingestion/closure boundary; Scene and adapters never receive
raw SVG/XML. PNG is byte-preserved, dimension-validated, and referred to only
by its closed identity. Network URLs, data URLs, script, event attributes,
foreign objects, external references, fonts, CSS, filters, masks, clipping,
animation, and arbitrary images inside SVG are rejected. The feature does not
admit generic image primitives, arbitrary SVG, package acquisition, or a rich
PDF/Typst/TikZ fallback.

## Required design decisions

1. **Resource and closure.** Define a versioned `chrona/icon-catalog/v0.1`
   envelope, typed Context edge, deterministic catalog/asset ordering, safe
   repository-relative asset addresses, identity verification, and materializer
   snapshot copying. A changed or missing asset must fail before Layout or
   rendering; a path is never an identity.
2. **Normalized icon model.** Define a renderer-neutral `Icon` primitive
   rather than extending `Symbol`. Its vector payload is a closed set of
   finite viewport-relative paths (including the cubic commands needed by
   ordinary icon artwork), fills, and viewbox; its raster payload is a closed
   identity with intrinsic dimensions. Scene contains complete icon bounds,
   scale, alternative, semantic role, and asset identity. It does not contain
   catalog lookup data or a host path.
3. **Layout composition.** Define a measured icon-plus-text placement with
   icon bounds, text bounds, baseline, typography, wrapping, overflow, gap,
   and reading-order metadata. Layout obtains normalized icon metrics from the
   resolved catalog and reserves the leading icon before measuring/wrapping
   text. Scene cannot choose an icon coordinate or measure text.
4. **Semantic authority.** Semantic/View policy decides that a role has an
   icon-leading label or icon mark; Theme binds the semantic role to catalog
   entry and tokenized treatment. A Theme cannot introduce a filesystem path,
   SVG syntax, concrete colour literal, or target fallback. A first public
   fixture must demonstrate both a leading label icon and an icon mark.
5. **Accessibility and capability.** Decorative icons are hidden from the
   accessibility tree and cannot be the sole bearer of meaning. Meaningful
   icons have a required catalog alternative and retain an equivalent textual
   semantic source. Required icon use has a named profile capability; an
   unsupported target diagnoses before serialization. Initial exact profiles
   are SVG and PNG only, with independent SVG/PNG evidence.
6. **Architecture alignment.** Amend Specifications 08, 13, 33, 62, and 63
   only at their ownership seams; give the feature a new owning specification,
   use-case/traceability entry, schema contracts, and whole-architecture
   review. Specification 63 continues to defer generic image capability while
   explicitly recognizing this narrow, closed catalog asset exception.

## Planned sequence

| Stage | Scope | Acceptance |
| --- | --- | --- |
| D350-1 | Resource, asset closure, security, and normalized vector/raster model | no raw asset or renderer syntax crosses into Scene; identities and failure modes are closed |
| D350-2 | Layout, semantic/theme, accessibility, and profile ownership | inline and mark placements have a single Layout authority; no target fallback leaks |
| D350-3 | Whole-architecture review, use-case, and traceability | all affected specifications agree; package and generic-image boundaries remain explicit |
| I350-1 | Catalog schema, typed closure, asset validation, and materialization | SVG/PNG assets verify/copy deterministically and hostile/mutated inputs reject |
| I350-2 | Normalized Icon Scene primitive and SVG/PNG profile serialization | adapters receive completed data only; target/profile failures are exact |
| I350-3 | Layout composition and semantic icon bindings | measured leading label and mark fixture project without Scene measurement or placement choice |
| I350-4 | Public gallery, materializer evidence, focused/full/conformance/wheel/CI gates | reusable fixture demonstrates both asset classes and all release evidence passes |

## Design-deviation rule

An added SVG feature, generic image, target adapter, package-acquisition route,
unclosed asset lookup, renderer-specific fallback, or icon-only required meaning
returns work to D350-1 through D350-3. No implementation may compensate with
adapter branches or direct file reads.
