# Design Correction: Ungrouped Scene row identity (#375)

**Status:** Accepted.

## Discovery

Complete corpus Scene generation exposed a v0.2 schema mismatch: runtime
`SceneRow.group_id` uses `""` for a row without a group, while the schema
incorrectly reused the non-empty identifier definition.  Representative v0.1
evidence happened to contain grouped rows and did not expose the mismatch.

## Decision

`groupId` remains a required field, because its presence distinguishes a
completed row record from a partial one, but it uses the general text contract
and permits the empty string as the explicit ungrouped value.  Row and object
identifiers remain non-empty.  No sentinel group, omitted key, or consumer-side
normalization is introduced.

## Architecture review

The correction aligns the schema with the typed runtime model without moving
group policy into serializer or coverage code.  It preserves the boundary:
Layout/projected rows decide grouping; Scene carries the completed fact;
coverage only reads the serialized result.

## Acceptance

* An ungrouped declared corpus slide validates as v0.2.
* Grouped and ungrouped rows remain distinguishable without a special parser.
* Full corpus Scene materialization proceeds through the public path.
