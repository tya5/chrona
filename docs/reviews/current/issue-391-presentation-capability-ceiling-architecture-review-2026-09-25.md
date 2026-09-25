# Architecture Review: Presentation capability ceiling (#391)

**Decision:** Accepted for implementation planning.

| Review concern | Result |
| --- | --- |
| View / Layout / Theme / Scheme authority | Pass — occurrence, geometry, treatment, and colour remain distinct owners. |
| Scene and adapter boundary | Pass — Scene completes the selected value; adapters cannot select omission or substitution. |
| Specification 63 fidelity | Pass — decorative rich paint remains two-valued; semantic substitution is capability-specific rather than an untyped expansion. |
| Specification 64 assets | Pass — normalized icons remain their own finite asset family. |
| Design Space / gallery | Pass — the registry supplies finite visual-grammar inspection facts without becoming a second presentation resource. |
| Package and closure rules | Pass — no package acquisition, registry lookup, or mutable selector enters rendering. |
| Clean migration | Pass — misplaced owner fields migrate atomically when their capability is implemented; no compatibility aliases are authorized. |

The decisive correction is refusing an unconstrained `substitute` enum.  Such
an enum would require either adapter-selected fallback or an unspecified Theme
convention, both of which violate the current authority model.  The accepted
design makes substitution possible only when a specific semantic encoding
introduces its finite alternative completion and target-profile evidence in the
same slice.
