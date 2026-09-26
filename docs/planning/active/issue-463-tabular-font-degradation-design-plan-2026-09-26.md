# Design Plan — Missing Tabular-Digit Degradation (#463)

## Published baseline

At `7fceda691fbd839e0d808990830bb6a09a430e36`, #447's host-font
correction permits a draft face to lack tabular advances but explicitly rejects
a Theme role requesting them. #463 reports successful host-face resolution for
Hiragino Sans and Georgia followed by this rejection. The existing immutable
font metrics contract and packaged corpus are independent of host-font choice.

Source: [Issue #463](https://github.com/tya5/chrona/issues/463). There are no
later issue comments at planning time. #459 is a separate P1 slice; #462 is
held by its owner and is not a dependency.

## Literal acceptance criteria

1. `chrona render --system-fonts` with Hiragino Sans or Georgia and a bundled Theme succeeds, with a warning naming the numeric role.
2. The committed corpus is unchanged, since its packaged faces have tabular digits.

## Design questions and boundaries

- Choose where a requested-but-unavailable numeric feature resolves to an
  effective feature: before Layout measurement, using the exact selected face.
  Scene and every renderer must receive and paint that same effective mode.
- Define structured warning identity, role/family/weight evidence, CLI/Scene
  transport, order and deduplication, without treating missing face or missing
  basic digit metrics as a harmless fallback.
- Decide whether an explicit `required` authoring mode is needed now; do not
  introduce optional syntax without a concrete owner and migration contract.
- Review Specification 43, font-metrics v3, #410, #447 and #449 against
  measurement/rendering parity and immutable-context reproducibility.
- Keep packaged descriptors and committed public corpus byte-identical unless
  an approved design correction explicitly changes them.

## Ordered independently publishable slices

1. Publish this baseline and design plan.
2. Publish selected design, normative changes if needed, and whole-architecture
   review before implementation planning is final.
3. Publish an implementation plan with affected owners, warning path, host-font
   fixtures, CLI/Scene tests, byte checks and CI gates.
4. Implement and review the approved slice; publish acceptance only when both
   platform-specific host evidence and corpus identity are checked.
