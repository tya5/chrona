# Issue 314 Declared Colour Scales Design Review

## Decision

Adopt the closed domain-to-named-slot scale of Specification 60.  It makes a
field-driven paint inspectable and total while retaining View selection,
Theme policy, Scheme literals, Layout geometry, Scene projection, and adapter
serialization as separate responsibilities.

## Rejected alternatives

| Alternative | Rejection reason |
| --- | --- |
| ordered predicates / the removed rule engine | rule order is visual authority, lacks a total coverage proof, and cannot derive a truthful legend |
| hash or positional category assignment | not author-predictable and cannot establish domain-to-swatch correspondence |
| colour literals on Project values | prevents scheme replacement and mixes semantic facts with appearance |
| renderer callback or target palette | has no closure validation or reproducible legend |
| profile-package presentation declaration | creates a second presentation vocabulary authority |

## Whole-architecture consistency

The scale consumes only selected, typed View projection facts and pinned
presentation resources.  It cannot affect Project identity, temporal facts,
Scheduling, Actuals, grouping, Layout allocation, or Scene primitive geometry.
Scene's existing appearance-completion stage is the latest permissible point to
apply the resolved lookup because a source primitive and its semantic role are
then known; it remains data-free in the sense that it receives a typed resolved
lookup rather than raw View/Theme/Scheme syntax.  The adapter sees only a
concrete `ScenePaint`.

The derived legend removes the present hand-authored role/label drift path.
Its content is resolved before Layout, so text measurement and placement remain
Layout-owned.  A `planned` scale does not imply an `actual`, snapshot, scenario,
or progress encoding; each future target needs a separate eligibility review.

## Atomicity requirement

The old Scheme array, Theme `category` bindings, free-form legend profile
entries, all Context references, fixtures, tests, and generated SVGs change in
one materializable release.  A compatibility parser would leave two paint
authorities and is prohibited.
