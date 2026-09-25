# Design Correction — Axis Tier Role and Label Contract (#405, #406, #407, #408, #400)

**Status:** Accepted correction before I1 implementation.

A View v0.17 axis tier has one renderer-neutral responsibility.  It declares
`unit`, positive `every`, and exactly one `role`: `band`, `grid-major`,
`grid-minor`, or `labels`.  A band or grid tier has no label attributes.  This
prevents a single declaration from silently controlling several independently
authorable visual effects and ensures every declared field has an operational
consumer.

Only a `labels` tier has a `label` object.  For a concrete unit it contains a
unit-valid `form`, `align` (`start|center`), and `overflow`
(`diagnose|thin-with-record`).  The finite form vocabulary is:

| unit | forms |
| --- | --- |
| day | `localized-date` |
| week | `iso-week` |
| month | `short-month`, `long-month`, `numeric-month`, `short-month-year`, `long-month-year`, `numeric-year-month` |
| quarter | `quarter`, `year-quarter`, `quarter-year` |
| half | `half-year` |
| year | `year` |

`unit: auto` is valid only for a labels tier.  Its `label.forms` maps one or
more concrete candidate units to their valid form.  Layout examines supplied
candidates in the fixed dense-to-coarse order, formats each candidate with its
own declared form, and selects the first that fits.  It never substitutes a
locale-derived form or an undeclared candidate.  `align` and `overflow` remain
properties of that label tier.

The array may contain separate tiers for the same unit, for example a quarter
band and quarter major grid.  This is deliberate: each placement is separately
observable, has one Scene role, and can later receive independent alternation
or grid policy.  `auto` cannot form a band or grid because there is no stable
geometry until a fitted label candidate has been selected.

This corrects unpublished I1 work only.  It introduces no legacy reader and
does not decide I2 calendar geometry, Scene role names, thinning records, or
I3 visible-failure policy.
