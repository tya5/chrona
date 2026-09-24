# Implementation Amendment: Overlay review-height token (#382)

**Status:** Accepted.

**Amends:** [Overlay corpus evidence implementation plan](issue-382-overlay-corpus-evidence-implementation-plan-2026-09-25.md)

Before I382-1 materialization, add `panel.review.block` to the current
wallboard Theme as a typed number.  Add it to `overlay-briefing`'s exact
`requiredThemeTokens`; replace content-sized review allocation with the token
fixed extent while retaining the guide offset and strict required slots.

Focused acceptance adds Theme/Layout exact-token validation and materializes
the complete 26-row programme board.  It does not alter existing layout
resources, View selection, or artifact bytes.
