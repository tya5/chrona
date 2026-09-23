# Design Correction Plan: Post-release Icon Ecosystem Reconciliation (#350)

**Status:** Active — replaces the premature R350-7 acceptance decision.
**Authority:** Specification 64, the #350 successor design, and the post-hoc
review recorded on #350 on 2026-09-24.

## Trigger and scope

The prior release review declared #350 accepted while two conformance gates
were red and while its documented Draft command could not select an icon-capable
profile.  The review also verified that the bundled Material catalog omits its
upstream aliases and usable short names, records an untrue `local` source
version, and lacks public Material-bearing small-text evidence.  These are
product-contract gaps, not release-note corrections.

This correction closes all verified findings without reopening the settled
authority chain:

```text
local Iconify input -> normalized catalog -> closed Context catalog set
  + explicit View request + exact target profile -> Layout -> completed Scene -> adapter
```

No implicit profile upgrade, renderer catalog lookup, raw SVG fallback, or
compatibility reader is permitted.

## Corrected design decisions

### C350-1 — Explicit Draft capability admission

`chrona render` and its guided equivalent accept the exact already-supported
`chrona-output/visual/v0.7-svg` and `.../v0.7-png` values.  An author who uses
`--icon-catalog` must explicitly select an admitting profile; the command must
not infer capabilities from a catalog path.  README examples state that exact
profile.  Baseline, PDF, Typst, and TikZ rejection behaviour is unchanged.

### C350-2 — Bundled Material naming and provenance

The generic importer preserves every upstream alias whose fully resolved parent
is present in the selected canonical entries.  It does not use an alias filter
as an accidental second selection filter.  Transform-bearing aliases remain
normalized entries; alias-parent chains are resolved before either outcome.

The bundled Material variant has an additional verified closure requirement:
1,707 upstream `*-outline-rounded` aliases resolve mostly to distinct
`*-rounded` canonical parents outside the original 2,336-entry selection.
The generator therefore includes the terminal parent geometry for every
declared variant alias and records the alias against that included canonical
entry.  It must not emit an alias that points outside the catalog.  The former
2,336-entry / 4MB bound is superseded: the generated manifest records canonical
selection count, alias-parent closure count, exact/gzip byte limits derived from
the regenerated catalog, and identity.  This is a correctness expansion, not a
runtime fallback or a compatibility bridge.

The bundled Material generation manifest owns an additional, deterministic
*bundle alias policy*: remove the exact `-outline-rounded` suffix only when it
maps to one bundled canonical entry and cannot collide with any canonical name
or alias.  This policy is specific to the bundled single-variant product
default, not a lossy generic importer rule.  Both the source package version
and source content identity are explicit manifest inputs; `local` is forbidden
for the packaged default.  The catalog continues to contain its complete notice
because a standalone copied catalog must retain licence evidence.

### C350-3 — Diagnostics and selection recovery

Import failure reports contain stable code plus source prefix, icon name, and
the offending XML element, attribute, or path stage.  Unknown icon references
contain the requested reference, searched catalog set, and deterministic nearest
canonical/alias candidates.  This extends the established diagnostic contract;
it does not make Layout perform catalog search.

Whole-collection atomicity remains the default and the CLI must name the first
failing icon.  An `--exclude` recovery mechanism changes the declaration of a
complete collection and is therefore deferred until a separately designed
collection-profile contract can record exclusions and their source identities.
It is not smuggled into this correction as an untracked line-list switch.

### C350-4 — Real-set conformance and supported-subset growth

The Python importer remains the runtime implementation: no Node dependency is
introduced.  A committed Material Symbols conformance fixture generated from a
pinned `@iconify/utils` release compares aliases, inherited dimensions, flips,
rotation, and resolved geometry.  CI reads the committed fixture only.  This
protects the hand-port at the third-party-format boundary.

`picosvg` is not added now.  Its adoption is triggered only by an approved
expansion from the current closed SVG subset to `defs`/`use`, clipping, or
stroke-to-fill.  Until then those features reject per icon with actionable
diagnostics, preserving the declared all-or-nothing import semantics.

### C350-5 — Evidence and release accountability

The public Controller Z corpus receives a bundled `material:` example at
small table text (13–14 px), header, and title sizes.  Reproducible materializer
and semantic SVG assertions prove name resolution, visible geometry, label
paint, and sizing.  Catalog load and Draft render performance receive bounded
tests using the C loader; no performance assertion relies on a reviewer’s
machine-only timing.

The release review is marked superseded until all correction slices pass full
suite, conformance, public materializers, wheel smoke, and CI.  The requirement
matrix gains correction rows rather than treating the previous R350 rows as
evidence of unverified closure.

The public materializer may close a package-owned catalog without duplicating
its bytes into an example.  Such a reference is explicit, has provider
`package`, a package resource address, and an exact content identity.  The
materializer copies those verified bytes into the same immutable snapshot as
other closure inputs.  It never discovers package resources by directory scan
and it applies the identical raster-asset validation if the catalog declares
one.  This is a closure ingress adapter only; Context resolution, Layout,
Scene, and adapters remain unaware of the source provider.  The copied
materialized Context rewrites that reference to its snapshot-local Store and
revision before resolution, so `LocalSnapshotReader` remains the sole renderer
read adapter.

## Design gates

| Gate | Required outcome |
| --- | --- |
| D350C-1 | CLI/profile and README form one executable public Draft path. |
| D350C-2 | Material alias-parent closure, unambiguous short names, provenance, and bounded loading are generated and identity-tested. |
| D350C-3 | Import/unknown-name diagnostics preserve source identity and actionable recovery data. |
| D350C-4 | Iconify-utils fixture proves importer alias/transform semantics offline in CI. |
| D350C-5 | Public Material 13px evidence, package-resource closure, and all release gates are reproducible and green. |

## Publication sequence

1. Publish this correction, architecture review, and corrected implementation
   plan; supersede the accepted release decision.
2. Repair command/schema/dispatch gate and publish green focused conformance.
3. Implement generic alias/diagnostic semantics, then regenerate the bundled
   catalog with explicit manifest inputs and public Material evidence.
4. Publish offline third-party conformance evidence.
5. Run complete release gates and publish a replacement acceptance review.
