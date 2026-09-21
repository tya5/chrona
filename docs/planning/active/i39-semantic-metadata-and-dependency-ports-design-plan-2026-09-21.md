# Issue 39 Semantic Metadata and Dependency Ports Design Plan

**Issue:** #39
**Status:** Active

## Objective

Restore completed Scene primitive semantics in SVG and anchor dependencies to mark ports without adding renderer inference or project-specific rules.

## Design steps

1. Audit ScenePrimitive field ownership, builder construction, SVG serialization, and relation endpoint facts.
2. Define keyword-only semantic field assignment and completed mark-port geometry.
3. Review compatibility with row/item composition and relation expansion.
4. Publish completed design, then implementation plan, then implementation.
