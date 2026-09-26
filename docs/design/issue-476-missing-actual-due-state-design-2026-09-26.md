# Design — Due-State Missing Actual (#476)

**Plans:** [initial](../planning/active/issue-476-missing-actual-due-state-design-plan-2026-09-26.md), [TVAC correction](../planning/active/issue-476-missing-actual-due-state-design-plan-amendment-2026-09-26.md). **Related:** #470, Specifications 06, 08, 25, 39 and 46.

## Selected semantics

The View comparison projection derives exactly one typed observation state per
selected Primary Project item:

| State | Predicate at the Actual set's explicit `asOf` |
| --- | --- |
| `recorded` | A selected Actual observation exists, even when its endpoint or progress is incomplete. |
| `due-unobserved` | No selected observation exists and the planned due endpoint is on or before `asOf`. |
| `not-yet-due` | No selected observation exists and the planned due endpoint is after `asOf`. |
| `unavailable` | No selected observation exists and no Actual as-of is declared for the render. |

The due endpoint is the canonical planned exclusive `end` for a span and
planned `at` for a point. Equality counts as due: `end == asOf` and
`at == asOf` both yield `due-unobserved`. A start-based “should have begun”
policy and a separate not-yet-due glyph are **not** introduced: no current
View contract declares either policy. The existing `missingActual` facet is
thus an overdue/at-due absence of an observation, not an incomplete finish.
No local clock, View window edge, label text or renderer coordinate may stand
in for `asOf`.

The public HALCYON Actual set contains `tvac-in-progress`, so shipped TVAC is
`recorded` and retains `W_LAYOUT_ACTUAL_INCOMPLETE:tvac` if its unfinished
observation cannot produce a complete Actual mark. To test the issue's
inclusive date boundary, a test-only HALCYON Actual-set copy removes only that
observation. The source corpus is not altered or mislabeled. The issue owner
has been asked to correct the literal “TVAC ... no observation” wording.

## One fact through all consumers

`ReviewItem.observation_state` is an immutable typed value computed once when
View aligns planned and Actual data. Automatic, explicit, shared and folded
rows propagate it unchanged. Snapshot/scenario members have `unavailable` and
must not masquerade as missing Primary Actuals. The state is not recomputed
from `bool(actual)` or dates in Layout, Scene or table formatting.

| Consumer | Required projection |
| --- | --- |
| Semantic roles | `missing-actual` only for `due-unobserved`; `actual` only for `recorded`; planned always remains. |
| `missingActual` table source | `true` for `due-unobserved`, `false` for `recorded`, and unavailable (`None`, rendered by the column's declared `missing` policy) for `not-yet-due` or `unavailable`. A future row must not read “Recorded”. |
| Table semantic role | `missingActualCell` only for `due-unobserved`; other states use ordinary table-cell presentation. |
| Summary `count.missingActual` | Count `due-unobserved` selected Primary items. Without an as-of, the metric is unavailable, not zero. |
| Layout track and mark | Reserve/emit missing-Actual geometry only for `due-unobserved`; reserve actual geometry only when an Actual mark can be emitted. An incomplete `recorded` observation retains its existing data-state diagnostic without a false missing mark. |
| Scene/adapters | Project completed primitives/paint and serialize; no due-date condition or mark repair. |

The View's `comparison.facets` still selects whether the missing-Actual mark
family is requested. A missingActual table column is independently declared
and consumes the same state even if the mark facet is not selected. The
selected state is a semantic fact; View selection controls presentation.

## Failure, extension and migration

An invalid Actual resource or misaligned observation keeps existing ingress
diagnostics. No new schema version, implicit fallback or silent treatment is
needed. If a future View explicitly adds started-state or not-yet-due
treatments, it must use a versioned policy and a separate visible semantic
role; it cannot change this finish/point due rule by Theme convention.

This is an intentional output migration: future unobserved work loses hollow
missing-Actual capsules; a declared `missingActual` table cell becomes its
missing placeholder instead of `Missing`/`Recorded`; summary counts fall to
the truthful due-unobserved set. Public Scene/SVG/PNG evidence affected by
this rule must be regenerated with the public materializer and reviewed as a
batch. Project, Actual and scheduler data are unchanged.

**Review:** [whole-architecture check](../reviews/current/issue-476-missing-actual-due-state-architecture-review-2026-09-26.md).
