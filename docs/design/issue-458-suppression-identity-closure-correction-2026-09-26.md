# Design correction — suppression identity closure (#458)

**Predecessor:** [#458 design](issue-458-as-of-label-suppression-design-2026-09-26.md).

The literal acceptance criterion covers every suppressed primitive, not only
ordinary labels. The public Scene diagnostic vocabulary has three relevant
forms:

| Diagnostic | Suppressed Scene primitive identity |
| --- | --- |
| `W_LAYOUT_LABEL_SUPPRESSED:<id>` | `<id>` |
| `W_LAYOUT_RELATION_SUPPRESSED:<relation-id>` | `<relation-id>` |
| `W_LAYOUT_RELATION_LABEL_SUPPRESSED:<relation-id>` | `relation-label:` plus `<relation-id>` without the leading `relation:` |

The serialized-Scene gate must check all three exact mappings against emitted
primitive IDs. Relation-label diagnostics name their parent relation rather
than their text placement; this explicit typed mapping is part of the existing
Layout/Scene identity contract, not a geometry inference. A match is an error
with the emitted primitive identity. New suppression families require an
explicit identity mapping and fixture before being covered; broad substring
matching is forbidden. No schema or adapter change is needed.
