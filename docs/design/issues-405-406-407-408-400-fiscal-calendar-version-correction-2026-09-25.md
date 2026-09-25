# Design Correction — Fiscal Calendar Contract (#405, #406, #407, #408, #400)

**Status:** Accepted correction before I1 implementation.

`timeline/project/v0.7` replaces v0.6 and adds an optional integer
`fiscalStartMonth` (1 through 12) to a named Project calendar. Its deterministic
default is January. A View tier may request quarter, half-year, or year
intervals, but it cannot state or override fiscal origin. Layout resolves the
selected Project calendar once and derives fiscal bucket boundaries from that
fact; locale, context title and adapter state are not inputs.

Project v0.7 and View v0.17 are one I1 migration unit. All corpus Projects,
Views, pinned Context identities, schema inventory, package resources, tests
and generated evidence move together. The prior versions have no runtime
readers. This is required because a View's typed tier is otherwise capable of
asking for a fiscal form whose semantic origin does not exist in the immutable
Project closure.
