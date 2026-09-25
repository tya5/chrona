# Architecture Review — Axis and Visible-Failure Design (#405, #406, #407, #408, #400)

**Decision:** Accepted, subject to these implementation constraints.

| Boundary | Result |
| --- | --- |
| View/Calendar/Layout ownership | Pass. Tiers are View intent; fiscal buckets derive from the Project calendar; Layout selects, measures, and records intervals. No adapter or locale host state determines a bucket. |
| Typography-aware measurement | Pass. Auto fitting and label overflow consume the same resolved font metrics and text as placement. P4 may extend typography later but cannot bypass this path. |
| Finite vocabulary | Pass. Per-unit enums and two explicit name tables replace a misleading cross-product. Arbitrary date formats and host locale lookup remain excluded. |
| Scene/output boundary | Pass. Selected tiers/outcomes become completed placement/Scene data. SVG/PNG never calculate ticks, thin labels, or invent a warning. |
| Immutable/draft boundary | Pass. Draft auto-height remains a draft accommodation. Immutable Context/materializer behavior stays explicit and reproducible; it cannot silently grow or substitute output. |
| Specification 50 | Pass. The failure taxonomy makes its no-silent-loss rule explicit, while allowing visible degradation to follow declared policy. |
| P1 dependency | Pass. P1 owns row requirement/allocation; P2 owns classification only. This avoids a second row algorithm. |

## Guardrails

1. A View tier cannot be silently ignored; normalization must reject an invalid
   unit/role/form combination before Layout.
2. `thin-with-record` must preserve full candidate identifiers and reason in
   placement/Scene diagnostics; it is not a visual-only choice.
3. Fiscal start is a declared calendar fact with one deterministic default;
   it cannot be inferred from Context locale or title text.
4. P2 must migrate all old `axis.levels`, `ticks`, and `timePresentation`
   resources atomically. There is no v0.15 reader.
5. The failure registry is finite and owned by Layout. It cannot become a
   generic exception suppressor or permit an adapter fallback.

The design is consistent with the current architecture and unblocks P1's
policy-dependent implementation plan.
