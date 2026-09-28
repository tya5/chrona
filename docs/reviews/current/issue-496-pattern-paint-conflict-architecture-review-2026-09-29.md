# #496 pattern paint conflict architecture review

**Decision:** Accept the [correction](../../design/issue-496-pattern-paint-conflict-correction-2026-09-29.md). Specification 64 places tile stroke geometry in the asset, Specification 07 owns Theme paint admission, and Specification 08 requires Scene/adapters to preserve completed values. Rejecting conflicting Theme properties prevents a second owner for ink geometry or an unused gradient/border declaration. This leaves existing Theme v0.11/v0.12, Scene v0.6, and non-catalog pattern paths unchanged.
