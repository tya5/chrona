# Reachable Presentation Release Acceptance Review

## Scope and merged evidence

This review accepts the six slices planned in
`issues-320-312-307-315-310-317-implementation-plan-2026-09-23.md`:

| Slice | Merged evidence |
| --- | --- |
| I320 | `7fb00b5` |
| I312 | `a56e1cb` |
| I307 | `eebf4ac` |
| I315-A | `6b196ec` |
| I310 | `cc33762` |
| I317 | `e7de25f` |

I315 remains open intentionally.  Opacity and literal-colour removal are
complete; stroke width, mixed fill/stroke, and dash remain tracked by #332.

## Architecture acceptance

Layout owns completed geometry, collision, fallback, and routing.  Scene now
projects those completed placements without measuring text or routing; Theme
and Scheme resolve visual policy; adapters serialize it.  Inside labels follow
the selected host mark through Layout anchor selection, Scene semantic role,
and Theme/Scheme pairwise contrast validation.  No renderer selects label
placement or contrast policy.

ScenePrimitive was reduced to fields with presentation consumers.  The CI
delivery checker rejects a newly declared field with no consumer.  The View
dispatch checker rejects a closed Layout dispatch without a View schema door;
it covers inside labels and every implemented axis formatter.

## Verification

On `e7de25f`, the release verification completed:

- public materializers: 9 passed;
- generated-output properties: 61 passed, 7 skipped;
- conformance: PASS;
- Scene field delivery: 17 fields consumed, none stale;
- View dispatch reachability: 10 values have schema ingress;
- module reachability and import direction: PASS;
- CI on the I310 and I317 merge commits passed on both macOS and Ubuntu,
  including the full pytest suite, wheel build, installation, and smoke test.

The generated SVG review is intentional: Controller-Z demonstrates successful
inside labels and outside fallback; HALCYON category-band changes follow the
existing Scheme content-identity category resolver after new required Scheme
ink values were introduced.  No unrelated generated artifact changed.

## Acceptance decision

The six planned slices are accepted.  Close #320, #312, #307, #310, and #317.
Leave #315 open, linked to #332, until the deferred paint vocabulary is
designed and delivered.
