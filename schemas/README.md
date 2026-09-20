# Project Schema v0.1 Notes

The structural schema intentionally does not encode every semantic rule.

Rules requiring semantic validation include:

- object profile determines whether schedule is Point or Span;
- fixed span requires `start < end`;
- dependency endpoint must exist on the referenced object type;
- WorkPeriod calendar must resolve;
- scheduled amount must be positive;
- fixed-target dependency is a validation condition;
- referenced IDs must exist;
- calendar exceptions must not contain contradictory duplicate dates.

Schema validation is therefore stage 1, not full Core conformance.

## Presentation schemas

`presentation-resource-v0.1.schema.yaml` defines the common Presentation resource
envelope and shared reference shapes. `render-context-v0.1.schema.yaml` is the first
kind-specific structural schema. It validates that a renderable evaluation explicitly
binds its Project revision, presentation resources, locale, viewport, target
capabilities, and layout metrics.

The fixture under `../fixtures/presentation/` is structural only. The companion View,
Style, Theme, and Scene profile resources deliberately use empty bodies until their
respective semantic languages are specified. Passing this schema must not be described
as a rendered-Scene or presentation conformance result.

`review-detail-profile-v0.1.schema.yaml` owns the M23 authoring resource for selected
group descriptions, milestone IDs, and source-labelled observation rows. The v0.2
Presentation Settings Detail remains the sole legend wording/order authority.

`layout-profile-v0.2.schema.yaml` is the M24 replacement authoring grammar for a
stable-ID composition tree, intrinsic/fractional sizing, logical alignment, and bounded
anchors/guides/barriers. `render-context-v0.4.schema.yaml` binds reusable Theme and
Layout resources separately. They are design-complete schemas and become the only
runtime path when M24 implementation deletes v0.1 Layout and bundled Preset authority.
