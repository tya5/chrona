# Design — Guided annotations and the guided grouping subset (#709)

**Plan:** [implementation plan](../planning/active/issue-709-guided-annotations-implementation-plan-2026-10-01.md).
**Found by:** #662 ([design D5](issue-662-schema-parts-design-2026-09-30.md), [architecture review F11](../reviews/current/issue-662-schema-parts-architecture-review-2026-09-30.md)).
Evolution rule: [Spec 56 §3.2](../specification/56-schema-authoring-and-diagnostics.md). The lead engineer fixed the decisions below before code; this note records them and the evidence.

## Problem

1. **A guided annotation cannot produce a View.** `authoring-workspace-v0.1` accepts `overrides.view.annotations[]` whose `anchor` is `{kind: object, id}`. View v0.28 requires
   `anchor.required: [kind, id, facet, endpoint]`. `_apply_view_overrides` appends the annotation as authored, so the anchor never gains the two members, and normalisation fails with
   `yaml.representer.RepresenterError` instead of an `AuthoringError`.
2. **The guided `grouping` choice is an unnamed subset** of View's `grouping.by`.

Reproduced on main `328d5689` with the helpers of `tests/unit/chrona/presentation/model/test_authoring.py` (a guided annotation with `anchor: {kind: object, id: firmware}`):
`RepresenterError: ('cannot represent an object', {'id': 'note-1', ...})`.

## Root cause of the `RepresenterError`

It is a defect, not a harness artefact. `parse_contract` freezes every mapping of the workspace into `FrozenDict` (a `dict` subclass) and every sequence into `FrozenList`. The window, grouping and
visibility overrides are copied by scalar (`{**a, **b}`, `{"by": value}`), so they reach the View body as plain data. `overrides["annotations"]` is the one override copied by reference: the
`FrozenDict` items go into the View body. `_identity` then runs `yaml.safe_dump(document)`, and `SafeDumper` represents an exact `dict`, not a subclass, so it raises `RepresenterError` before any View
validation. The same hazard exists for any future override that is copied by reference.

**Decision D1 (make it impossible).** `_apply_view_overrides` takes a plain-data copy of the override (`deepcopy`, which `FrozenDict` and `FrozenList` already define to return plain `dict` and `list`)
before it reads it, so no frozen container can reach a source document. The normalised sources are therefore plain data by construction, and a test asserts that every returned source contains only
`dict`, `list` and scalar types. Any remaining failure in normalisation is an `AuthoringError` with a stable code (`E_AUTHORING_NORMALIZATION`, `E_AUTHORING_ANNOTATION_ID`, ...); a View that the
normalised sources fail to parse surfaces as `AuthoringError`, never as a raw representer or schema exception.

Found while testing (I709-A): the duplicate-id check compared the guided annotations only with the preset View's, so two guided annotations with one id passed normalisation. It now also rejects a
duplicate among the guided annotations (`E_AUTHORING_ANNOTATION_ID`). No committed document uses a guided annotation, so nothing that was accepted is newly refused.

## Decision D2. The guided annotation works; missing anchor parts are defaulted

The guided annotation is an author-facing, agent-friendly path and is meant to work. authoring-workspace v0.1 is **not** tightened (requiring `facet` and `endpoint` would narrow an accepted
document). `_apply_view_overrides` completes the anchor by a documented rule:

| Anchor member | Default | Why |
| --- | --- | --- |
| `facet` | `planned` | Every guided task is a planned `fixed-span` object, so a planned mark always exists; an Actual mark exists only when the author recorded an observation. The committed View annotations anchor `planned` in 8 of 10 anchors. The guided annotation names an object and offers no way to ask for an Actual, so the default is not a substitution for a missing mark (Spec 30 forbids that fallback in the Scene; this is an authoring rule applied before the View exists). |
| `endpoint` | `finish` | A fixed-span object has `start` and `end`, so `finish` resolves (`resolve_annotation_anchor`). The guided vocabulary already calls the span end `planned.finish`. Among the 10 committed single-line object anchors in `examples/`, `conformance/` and `docs/`, `finish` is the most used endpoint (5; `at` 3, `body` 2), and the only span endpoint used. Spec 06 calls `end` the canonical spelling and `finish` its alias with an identical Scene, so either is correct; `finish` matches what the examples and the Scene ids already say. |

Neither the View spec (06, 30, 37) nor the View annotation tests state a default anchor; the choice follows the committed examples as the lead directed. The rule is per member, so an anchor that
somehow already carries `facet` or `endpoint` keeps it (the closed workspace schema does not allow that today, see D3).

An annotation whose object is not a task of the workspace is unchanged by this rule: the Scene reports it (`E_PRESENTATION_ANCHOR_MISSING`) as for a hand-written View.

## Decision D3. No explicit `facet` / `endpoint` in the guided anchor

Spec 56 §3.2 lets a View, Layout Profile, Project or Theme take an optional property in place. authoring-workspace is not in that list, and the in-place insertion would change the dereferenced
form of `authoring-workspace-v0.1` (an L1 delta of the S0 equivalence gate, to be listed in `conformance/schema-equivalence/expected-deltas-v0.1.yaml`, which other work edits concurrently), would
need the `actual` facet to be checked against the workspace's observations, and is not needed to make the path work. This change keeps the defaults-only rule. Allowing an explicit optional
`facet` and `endpoint` is a possible additive follow-up the owner can open; it needs no bump if it is optional.

## Decision D4. Name the guided `grouping` subset

Same pattern as `guidedAnnotationVisibilityMode` and `guidedRelationVisibilityMode`: in `vocabulary-v0.1`, `viewGroupingBy` (View's `grouping.by`: `objectType, field, hierarchy, none`) and
`guidedViewGroupingBy` (`objectType, none`), both untyped enums so a site keeps its dereferenced form, with a subset-of-superset test (proper subset, order kept) and a site test for each definition.
The vocabulary part is frozen once published, so the two definitions are added with their own frozen digests and the inventory lists them; no existing definition changes.

The sites adopt the definitions only if the S0 gate (`--base-rev origin/main`) reports L1 equal for `view-v0.28` and `authoring-workspace-v0.1`. The View site carries a `description` beside the
`enum`; the existing adopted sites show a site description does not change the fingerprint, and the gate decides. If L1 is not equal, the definitions and tests are added without adoption and the
reason is recorded in the PR. Result (I709-B): the gate reported `L1 structural (base origin/main): equal=45`, so both sites adopt the definitions; L2 and L3 are unchanged.

## Out of scope

- No change to authoring-workspace's schema, View's schema or any committed Scene byte. A change that alters a committed Scene byte or newly rejects a committed document stops the work.
- The acceptance review of #709 (the lead writes it) and the #454 board.

## Acceptance (from the issue)

1. The guided annotation either works or is rejected clearly: it works (D2) and any failure is an `AuthoringError` (D1).
2. An end-to-end test: a guided annotation yields a valid View and a rendered Scene containing the annotation.
3. The guided `grouping` subset is named and tested like the other guided subsets (D4).
