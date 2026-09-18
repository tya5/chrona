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
