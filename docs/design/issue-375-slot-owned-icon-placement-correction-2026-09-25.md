# Design Correction: Slot-owned icon placement (#375)

**Decision:** Accepted.

## Corrected ownership rule

Every `IconPlacement.slot_id` is a completed Layout fact at construction.  An
icon inherits the exact resolved slot of its Layout host; it never receives a
generic optional-slot fallback.  `SurfacePlacement.assert_valid()` remains the
single closure check before Scene projection.

For text-hosted visuals, Layout first resolves the host placement's owner:

* a valid explicit slot ID is retained;
* a `group-header` collision domain resolves to the table slot, because the
  group header is table geometry; and
* any other unresolved domain is a Layout ownership error.

The resolver is used both when normalizing completed text and when constructing
candidate plot/variance-label icon geometry.  Thus an icon and its host share
one already-resolved Layout owner even where the candidate is chosen before
the final text collection is emitted.

Annotation-box and note-index icon geometry is constructed in the annotation
branch, where the resolved annotation slot is already an explicit Layout fact;
those icons receive that slot directly.  Mark visuals continue to inherit the
mark's completed slot.

## Rejected alternatives

* Default all incomplete icons to `annotations`: makes an optional Layout slot
  an undeclared dependency and fails non-annotation surfaces.
* Recover ownership in Scene from visual ID text, primitive role, or bounds:
  recreates producer policy below the Layout boundary.
* Require an annotation slot for every surface: changes Layout grammar and
  constrains unrelated title, table, group-header, and plot visuals.

## Architecture alignment

| Boundary | Responsibility after correction |
| --- | --- |
| View | Declares a closed visual target only. |
| Layout | Resolves host geometry and its exact slot identity. |
| Placement | Carries completed icon and host slot identity. |
| Scene | Projects the supplied icon slot identity verbatim. |
| Coverage | Reads serialized completed ownership without interpretation. |

The correction preserves the `View → Layout → Scene` direction, leaves public
View syntax unchanged, and avoids a new Scene policy.  It closes an I375-0
placement invariant rather than changing the v0.2 contract.

## Acceptance

* The three exposed draft cases render without an annotation slot.
* Text-hosted, candidate-label, annotation, and mark icons each name a declared
  Layout slot before Scene projection.
* A missing owner is rejected by Layout; no Scene fallback is introduced.
* Existing materialized output is byte-identical, aside from no intentional
  public artifact change.
