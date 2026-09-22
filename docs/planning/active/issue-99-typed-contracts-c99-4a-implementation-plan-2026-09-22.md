# Issue 99 Step 4 / C99-4A — Typed Closure Foundation Implementation Plan

**Status:** Approved implementation plan.  **Design authority:**
`issue-99-typed-contracts-design-plan-2026-09-22.md`, merged by PR #115 at
`166e516`.

## Scope

Implement the mandatory typed closure foundation only: the render context,
project, view, theme, color scheme, layout profile, and the derived resolved
theme.  This slice establishes exact-schema-first construction and a single
`RenderClosure` access point without changing scheduling, layout, Scene,
renderer, optional profiles, schemas, or public SVG output.

## Design commitments implemented by this slice

- Add `presentation/contracts` as the only place that selects an exact schema
  and constructs frozen presentation contracts.
- Represent identity separately from contract data.  A `ClosureResource` has a
  typed `contract`, not `value`.
- Deep-freeze accepted payload values at construction.  Contract APIs expose
  named `body`/`facts` fields as read-only mappings for domain owners that
  already own their detailed interpretation; they do not expose a decoded YAML
  envelope or permit mutation.
- Parse the render context into a `RenderContextContract`, including typed
  reference, environment, and target fields.  Resolve the theme into a frozen
  `ResolvedThemeContract` during closure construction.
- Replace the `(dict, tuple[ClosureResource, ...])` result with a
  `RenderClosure`.  Update the CLI and render use case to consume it directly.
  The use case accesses contracts by typed getters, not kind strings or raw
  dictionaries.

## Files and changes

| Area | Change |
| --- | --- |
| `presentation/contracts/` | frozen mapping/list conversion; identity/reference records; contract classes; exact-schema registry and construction functions. |
| `presentation/model/closure.py` | decode/read/identity checks and closure assembly only; remove `ClosureResource.value` and `resolvedTheme` mapping injection. |
| `presentation/color_scheme.py` | accept `ThemeContract` / `ColorSchemeContract`, return `ResolvedThemeContract`; preserve existing diagnostics. |
| `usecases/render_review.py` | `RenderRequest` receives `RenderClosure`; typed closure getters feed the existing scheduler, projection, content, and layout calls. |
| `app/cli.py` and direct tests | adapt to the new resolved-closure return value; do not retain a tuple/dict compatibility overload. |
| focused contract/closure/use-case tests | exact-schema-before-contract, immutability, identity mismatch, typed getters, and byte-characterized render. |

## Steps

1. Inventory the exact current schema for each mandatory resource.  Register
   only versions materialized by the five public contexts.  A resource with no
   exact acceptance schema must remain outside this slice rather than fall back
   to the generic presentation envelope.
2. Implement frozen primitives and contract constructors.  Validate each
   decoded mapping with its exact schema before construction; map validation
   failure to the existing closure diagnostic.  Keep content identity and
   reference-ID checks in closure assembly.
3. Introduce `RenderClosure`, migrate mandatory resource loading and resolved
   theme construction, then remove the generic `value` field.  Preserve
   snapshot/optional handling unchanged for C99-4B, except that their existence
   remains represented as not-yet-consumable typed resources rather than a
   compatibility dictionary.
4. Migrate the CLI/render use case mandatory path.  Preserve each pipeline
   stage and pass contract-owned semantic data only to the existing domain
   owners.  Do not move normalization before measurement as part of this slice.
5. Add structural and characterization evidence, then run focused tests, full
   pytest, import/reachability lint, conformance, five public materializer
   checks, and a generated-SVG diff.  Do not update generated artifacts.

## Acceptance criteria

- Every C99-4A resource is accepted only by its exact schema before a frozen
  contract is created.
- `RenderClosure` has typed mandatory getters and has no generic
  `dict`/`ClosureResource.value` escape hatch.
- The render use case has no string-kind closure lookup and no access to
  `context["resolvedTheme"]`.
- Mutation attempts against a contract's body/facts fail, and post-construction
  mutation of a decoded source cannot influence its contract.
- Existing closure diagnostics, scheduler semantics, and all five public SVG
  bytes remain unchanged.

## Non-goals and hand-off

Optional review contracts, snapshots, profile packages, summary/detail content,
and their consumers are C99-4B.  Elimination of all generic closure-consumer
forms and the input-read structural gate is C99-4C.  Renderer/Scheduler
protocols are Issue #99 Step 5 and must not be introduced here.

## Publication boundary

This plan is published alone before implementation.  C99-4A implementation is
one PR based on the merged plan; C99-4B cannot begin until it has merged.
