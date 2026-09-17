# ADR-0006: Separate View, Style, and Theme

**Status:** Accepted for design direction

## Decision

Use the responsibility split:

```text
View  = selection and layout
Style = semantic-to-visual rules
Theme = concrete visual values
```

## Consequences

Views do not own colors; themes do not know project status semantics; styles bridge
semantic state to visual roles.
