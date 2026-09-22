# Schema inventory

`schema-inventory-v0.1.yaml` is the exact machine-checked lifecycle index.
Only `live` entries are authorable current contracts. `transitioning` entries
are migration-only and record their successor and removal slice.

| Kind | Live schema |
| --- | --- |
| actual-intake-batch | actual-intake-batch-v0.2.schema.yaml |
| actual-set | actual-set-v0.2.schema.yaml |
| automation-result | automation-result-v0.1.schema.yaml |
| color-scheme | color-scheme-v0.1.schema.yaml |
| command-request | command-request-v0.2.schema.yaml |
| layout-profile | layout-profile-v0.2.schema.yaml |
| profile-package | profile-v0.2.schema.yaml |
| project | project-v0.5.schema.yaml |
| render-context | render-context-v0.8.schema.yaml |
| review-detail-profile | review-detail-profile-v0.1.schema.yaml |
| snapshot-ref | snapshot-ref-v0.2.schema.yaml |
| store-config | store-config-v0.1.schema.yaml |
| summary-profile | summary-profile-v0.2.schema.yaml |
| theme | theme-v0.2.schema.yaml |
| view | view-v0.6.schema.yaml |

# Project Schema v0.3 Notes

The structural schema intentionally does not encode every semantic rule.

Rules requiring semantic validation include:

- object profile determines whether schedule is Point or Span;
- fixed span requires `start < end`;
- dependency endpoint must exist on the referenced object type;
- WorkPeriod calendar must resolve;
- scheduled amount must be positive;
- fixed-target dependency is a validation condition;
- referenced IDs must exist;
- parent references form an acyclic forest and explicit WBS codes are unique;
- a rollup has descendants and derives their completed schedule envelope;
- calendar exceptions must not contain contradictory duplicate dates.

Schema validation is therefore stage 1, not full Core conformance.

## Presentation schemas

`presentation-resource-v0.1.schema.yaml` supplies shared envelope and reference
definitions for the listed Presentation resources. The current
`render-context-v0.8.schema.yaml` binds immutable Project and presentation
references, viewport, locale, measured font assets, and one declared target.
`layout-profile-v0.2.schema.yaml` defines the current intent-oriented composition
grammar. `review-detail-profile-v0.1.schema.yaml` owns selected group descriptions,
milestone IDs, and source-labelled review detail.
