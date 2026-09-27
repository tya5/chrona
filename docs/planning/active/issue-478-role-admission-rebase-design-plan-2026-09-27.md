# Design Plan Amendment — Rebase Role/Property Admission (#478 I478-3)

**Predecessor:** [#478 design plan](issue-478-declared-treatment-visibility-design-plan-2026-09-26.md),
[selected design](../../design/issue-478-declared-treatment-visibility-design-2026-09-26.md),
[architecture review](../../reviews/current/issue-478-declared-treatment-visibility-architecture-review-2026-09-26.md),
and [implementation plan](issue-478-declared-treatment-visibility-implementation-plan-2026-09-26.md).
**Published baseline:** GitHub `main` at `eff9780e` on 2026-09-27. I478-1
and I478-2 are accepted. I478-3 has no published product implementation.

## Why the design must be revisited before code

The selected contract and I478-3 plan counted 15 public Themes and 21 public
materializers. Current `main` has 17 example Theme resources, seven packaged
preset Theme resources, and 28 manifest slide targets. The new resources came
with #429, #465 and the other presentation releases. The original role examples
also predate #466's `annotationContainer` geometry and #465's image-backed
container, which uses an icon-catalog asset, nine-slice/content insets and a
representative fill for contrast. These are published facts, not uncommitted
work. A validator built from the old census could silently skip a public
resource or reject a valid new declaration.

## Literal acceptance unchanged

1. Rendering `elevated-light` under the default profile emits a diagnostic that names the dropped treatment and the profile that would paint it.
2. A Theme property on a role that cannot carry it is diagnosed at load time.
3. Suppressed plot labels are counted in an info diagnostic, or the View can ask for a visible marker on rows whose label was suppressed.

Rows 1 and 3 have published I478-2/I478-1 evidence. This amendment concerns
row 2 and the issue-wide release audit, without adding a new public feature.

## Design questions and ownership review

1. Enumerate the 24 current public Theme roots separately from intentionally
   invalid conformance fixtures. Trace each declared role/property through
   Theme inheritance, Scheme insertion and its actual Layout/Scene/adapter
   consumer. Resolve the exact materializer target list from manifests at
   verification time; do not freeze the earlier 21-target count.
2. Treat `annotationContainer` as a **Theme role property consumed by Layout**,
   not as a Scene paint effect or a new resource kind. Define which annotation
   box roles may bind it. Check how its nested value is validated by the
   Theme schema, resolved by `ThemeTokenView`, and asset-pinned by closure;
   preserve exact nested source pointers without inventing a second parser.
3. Review the now-live group-header/band, axis-cell, milestone-glyph,
   image-backed note, and preset roles. Separate authoring roles from Scene
   visual roles and conditional primitive families. No wildcard admission
   solely to make existing YAML load.
4. Check the one admission point after effective inheritance and Scheme
   binding, diagnostic pointer provenance for direct and Scheme declarations,
   and the atomic migration boundary. Assess intended incompatibilities and
   whether any normative Specification 07/08/63/64 text needs correction.

## Ordered deliverables and evidence

1. Publish a design correction with a finite role/consumer contract and
   current source inventory, or state precisely which existing contract
   remains unchanged. Record schema/token/asset boundaries and failure rules.
2. Publish a whole-architecture review against Specifications 07/08/50/63/64,
   #465/#466 and Theme inheritance, Layout, Scene, adapters, CLI and closure.
3. Publish an I478-3 implementation-plan amendment listing source owners,
   exact public Theme roots (or a manifest-derived rule), conformance fixtures,
   focused tests, generated evidence, and an atomic release/CI gate.
4. Only then implement the approved validator and resource migration. Batch
   check every current public materializer, inspect Scene/SVG/PNG effects and
   publish the implementation and literal acceptance reviews separately.

If role-to-consumer evidence is incomplete, keep I478-3 paused at design;
do not add a permissive exception or delete a declaration by name similarity.
