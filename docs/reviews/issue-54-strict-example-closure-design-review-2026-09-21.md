# Issue #54 opt-in closure correction design review

| Boundary | Result |
| --- | --- |
| #44 resource references | Optional `contentIdentity` remains authoritative. |
| Materializer | Copies authored bytes and verifies supplied pins only; no unconditional strict flag. |
| Closure resolver / reader | Existing optional verification remains the sole identity validator. |
| Font assets | Optional pin preserved; supplied incorrect pin is materializer-owned diagnostic. |
| Canonical examples | Stay unpinned and reproduce generated evidence through the public command. |
| PR #53 | Rejected: full-pin conversion would encode a policy not selected for examples. |

No renderer or Settings/Theme compatibility path is introduced. The correction restores one
identity policy across storage, closure, materializer, and examples. All design decisions are
closed; implementation may start only from the accompanying plan.
