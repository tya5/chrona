# Issue 94 Completion — Design Plan

**Status:** Active design plan.  This plan starts from `233593b`, after the
merged Phase 1/2 (#96), Render Context v0.5 portion of Phase 4 (#97), and
partial Phase 5 (#98).

## Purpose

Issue 94 removes code and input ambiguity that are not part of the current
product path.  It does not broaden the product surface.  In particular, a
library design described in the use-case catalog is not a reason to make an
unreachable module appear product-reachable.

## Confirmed baseline

The reachability check has one CLI root plus conformance and tool script roots.
It reports 46 reachable modules and 19 deliberately staged modules.  The seven
unreachable presentation modules were deleted in #96; the check is run by CI.
The v0.5 Render Context and dual v0.5/v0.6 resolver have been deleted in #97.
#98 made resource envelopes and the CLI identity flag strict, but
`SurfaceContentInput` still permits construction of an empty rendering input.

## Decisions

### D94-1: delete, do not pretend-wire, the staged modules

The following modules have no current product entry point.  They are optional
future library sketches, not implementations of a published CLI route.  They
and their dedicated tests will be deleted together:

| Family | Modules |
| --- | --- |
| interactive / commands | `app.interactive`, `commands.ai_proposals`, `commands.commands`, `commands.editor`, `commands.gestures`, `commands.view_commands` |
| collaboration / extensions | `collaboration.collaboration`, `collaboration.federation`, `extensions.extension_registry`, `extensions.package_lifecycle` |
| intake / release | `presentation.model.actual_intake`, `release.output`, `release.release_package`, `release.successor_release` |
| successor scheduling | `scheduling.capacity`, `scheduling.cost_observations`, `scheduling.datetime_migration`, `scheduling.datetime_scheduler`, `scheduling.temporal_datetime` |

This decision leaves the documented use cases as design/library intent where
appropriate.  It does not claim that their deletion removes a current CLI
capability.  A future feature must enter through an explicit product-boundary
design and public-boundary test; it may not revive code by listing it as staged.

### D94-2: resource kind names, rather than one shared presentation number

Every current resource kind gets a kind-specific version namespace.  The
existing bodies and validation rules do not change in this phase:

| Current | Canonical |
| --- | --- |
| `chrona/presentation/v0.1` Actual set | `chrona/actual-set/v0.1` |
| `chrona/presentation/v0.1` summary profile | `chrona/summary-profile/v0.1` |
| `chrona/presentation/v0.1` style | `chrona/style/v0.1` |
| `chrona/presentation/v0.1` legacy ASTER Views | `chrona/view/v0.1` |
| `chrona/presentation/v0.2` View | `chrona/view/v0.2` |
| `chrona/presentation/v0.6` Render Context | `chrona/render-context/v0.6` |

Schemas, fixtures, closure validation, materializer diagnostics, and help text
will accept exactly these canonical strings.  Old strings are deleted rather
than normalized.  This makes resource identity unambiguous without retaining a
dual-acceptance migration path.

### D94-3: complete construction is the only Scene input

`SurfaceContentInput` is an internal completed-input value.  All fields used by
the surface must be explicit constructor arguments; only fields that have a
semantic, documented absence may remain optional and must use `None`, not a
silent empty tuple.  The normalizer remains the sole construction site for the
public materializer path.  Unit fixtures construct complete values deliberately.
A missing required input raises at construction, before Layout or Scene.

### D94-4: one normative geometry seam

Specification 08 will normatively state the handoff: Layout produces completed
geometry, Scene projects those placements to ordered renderer-neutral
primitives, and renderer adapters serialize primitives.  Specification 50 is
the detailed Gantt specialization.  Scene must neither measure text nor search
for coordinates/routes; renderer adapters must not infer geometry or policy.

## Delivery slices

1. **P94-3 — staged-module deletion.** Delete the 19 modules and their tests,
   empty `staged_modules.txt`, and retain the lint with zero staged modules.
2. **P94-4 — canonical resource identities.** Change schemas, examples,
   validators, fixtures, and diagnostics atomically; regenerate only intentional
   public artifacts.
3. **P94-5 — completed content construction.** Remove remaining defaulted
   `SurfaceContentInput` acceptance and add negative construction tests.
4. **P94-6 — normative seam and acceptance review.** Amend Specification 08,
   review it against Specifications 09/50 and ADR-0031, then publish the final
   #94 acceptance review.

Each slice has an independent PR.  Before each merge: focused tests, full
pytest, reachability lint, five public materializer checks, generated-SVG diff,
and a remote-main/PR-state check.  No force push or compatibility shim is used.
