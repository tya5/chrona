<!-- chrona:literal-acceptance/v1 -->

# Issue #709 — guided authoring-workspace annotations acceptance review

Source: [Issue #709](https://github.com/tya5/chrona/issues/709), observed 2026-10-01 (no comments; body unchanged since 2026-09-30). Found by #662. The issue has no Acceptance section: it states two findings and a "To decide" list, and those items are treated as the criteria below, quoted from the issue. Design and plan, published in [PR #749](https://github.com/tya5/chrona/pull/749) (merged as [`6d234dc4`](https://github.com/tya5/chrona/commit/6d234dc4da3a47a80ed5c2b9d5cc2729c24119ab), [PR CI](https://github.com/tya5/chrona/actions/runs/36822331805)): [design](../../design/issue-709-guided-annotations-design-2026-10-01.md) and [implementation plan](../../planning/active/issue-709-guided-annotations-implementation-plan-2026-10-01.md). Code: [PR #752](https://github.com/tya5/chrona/pull/752) merged as [`be1488fd`](https://github.com/tya5/chrona/commit/be1488fd919fca0468bddf38785408f9ab0810a6) ([PR CI](https://github.com/tya5/chrona/actions/runs/36826799822)); [PR #758](https://github.com/tya5/chrona/pull/758) merged as [`e9eeec1b`](https://github.com/tya5/chrona/commit/e9eeec1b984f3f08f3068c8c2f6fa996312f2822) ([PR CI](https://github.com/tya5/chrona/actions/runs/36830234288), `derived-ready` red only for a stale base, see the disclosures).

## Literal issue acceptance

### Issue #709

- Source: [Issue #709](https://github.com/tya5/chrona/issues/709)
- Observed: 2026-10-01

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Is the guided annotation meant to work? If yes: require `facet` and `endpoint` in the guided anchor (a tightening of authoring-workspace v0.1, to classify under Spec 56 §3.2) or default them in `_apply_view_overrides` (a documented rule), and make the failure an `AuthoringError`. | met | The owner-delegated decision was that it is meant to work, by a documented default and not by narrowing an accepted document: `facet: planned` and `endpoint: finish` in `GUIDED_ANCHOR_DEFAULTS` ([PR #752](https://github.com/tya5/chrona/pull/752)). Neither the View spec (06, 30, 37) nor the View annotation tests states a default, so the defaults follow the committed examples: of the 10 single-line object anchors in `examples/`, `conformance/` and `docs/`, 8 use `planned` and 5 use `finish`, and every guided task is a planned fixed-span object, so a planned mark and its span end always exist; Spec 06 calls `end` canonical and `finish` its alias with an identical Scene. The `RepresenterError` was a real defect: `parse_contract` freezes workspace mappings into `FrozenDict`, a `dict` subclass, every guided override reached the View as a plain copy except `annotations`, which went in by reference, and `yaml.safe_dump` in `_identity` cannot represent a `dict` subclass. The fix is a `deepcopy` of the annotation override, so the cause is gone and not caught, and a [test](../../../tests/unit/chrona/presentation/model/test_guided_annotations.py) asserts every normalised source is plain `dict`, `list` or scalar. An explicit optional `facet` and `endpoint` on the guided anchor was not added: it would change the dereferenced form of authoring-workspace v0.1, and a test pins that the closed schema still refuses them (design D3). | — |
| 2 | Whichever it is, add an end-to-end test that a guided annotation yields a valid, rendered View. | met | The [end-to-end test](../../../tests/unit/chrona/presentation/model/test_guided_annotations.py) goes from a guided workspace to a valid View to a rendered Scene containing the `note-1` box, text and leader, and checks the text appears in the SVG, using the committed controller-z annotation View, Layout Profile, Theme and Scheme. The same file has a test per default and the original reproduction as a regression. Mutation checks: removing the facet default fails 7 tests, removing the endpoint default 7, changing `finish` to `start` 3, removing the deepcopy 6, and removing the duplicate-id check 1; each was restored. | — |
| 3 | Add a `viewGroupingBy` definition and a `guidedViewGroupingBy` subset the same way (an untyped enum so a site keeps its dereferenced form), with the test that the subset is contained in the superset. | met | [PR #758](https://github.com/tya5/chrona/pull/758) adds both definitions to the [`vocabulary` part](../../../schemas/vocabulary-v0.1.schema.yaml) as untyped enums with digests in the inventory. The S0 gate showed L1 equal (45 schemas), so both sites adopt them: View `grouping.by` references `viewGroupingBy` and the authoring-workspace `grouping` site references `guidedViewGroupingBy`. The [vocabulary tests](../../../tests/unit/tools/test_vocabulary_part.py) cover the enum values, each site, subset-of-superset, that the guided subset carries no `field` or `hierarchy`, and that View accepts every guided value; adding `field` to the guided enum fails 3 tests. A wheel build and `tools/wheel_smoke.py` passed, and the installed wheel carries both definitions. | — |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

Authoring normalisation and the vocabulary part only; no schema version changed and the S0 gate showed no verdict change, so a guided workspace that was accepted before is accepted now, and a guided annotation that used to crash with a raw `RepresenterError` now yields a valid, rendered View.

Disclosures:

- **A merge with `derived-ready` red.** [PR #758](https://github.com/tya5/chrona/pull/758) was merged under the stale-base exception: `main` kept moving (derived bot commits and the #687 and #731 merges), the author rebased three times, and the final base check said stale base. Every other check was success (classify, derived-preview, three pytest shards, pr-conformance, newest-Python), the S0 gate on the rebased head showed 44 equal schemas and no delta, and `derived_evidence --check` passed; the merge body says so.
- **The defaults are a choice, not a specification.** The View spec states none; they follow the committed examples. If a different default is wanted it is one line in `GUIDED_ANCHOR_DEFAULTS`.
- **An extra fix.** The duplicate-id check compared guided annotations only with the preset View's, so two guided annotations with one id passed; it now rejects that with `E_AUTHORING_ANNOTATION_ID`. No committed document uses a guided annotation.
- **Derived effect.** The source edit shifts diagnostic line numbers, so CI's derived-sync regenerates `docs/diagnostics/inventory.md`.

Exact review-bearing-main three-OS CI and newest-Python materializer run must pass before closing #709; record that run in the issue closing comment.
