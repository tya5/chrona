# Architecture Review — Open Role Family Overlap (#478)

**Reviewed:** the [overlap correction](../../design/issue-478-open-role-family-overlap-correction-2026-09-27.md),
the #426 axis-tier and #427 legend contracts, Specifications 07/33/39,
View v0.24/v0.25 and Detail Profile schemas, Layout axis composition and
legend fallback, Scene ordinal axis paint, and Theme/Scheme closure.

**Decision:** accept a bounded union only for otherwise unregistered role
names. This is forced by two published open-name producers and Theme load's
intentional lack of a selected View/Detail Profile. It does not broaden any
known role, alter layer ownership, change Theme syntax, or infer consumer
intent from a name. The direct and Scheme diagnostic pointers remain exact
for properties outside the union. The previous custom-axis-paint negative
test is invalid and is replaced by a known-axis negative plus an unknown
dual-potential positive and Scene ordinal-paint projection test.

**Residual risk:** a misspelled paint role can still be a legal legend-only
role. An unused-role lint would require a selected context and its own
design; it must not be simulated by this load-time capability check.
