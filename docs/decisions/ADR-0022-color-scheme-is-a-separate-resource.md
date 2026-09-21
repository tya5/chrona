# ADR-0022: Color Scheme is a separate resource

**Status:** Accepted

## Decision

Introduce an immutable, versioned Color Scheme resource that owns concrete semantic and categorical colors. Theme owns a complete mapping from role paint properties to a closed Scheme-intent vocabulary, plus all non-color visual tokens. Render Context binds both resources and resolution produces one concrete internal Theme before measurement.

M25 deliberately removes Theme-local literal colors rather than retaining a fallback or compatibility branch. This gives every paint one authority and makes a selected Scheme a complete, reviewable color closure.

## Consequences

Scheme selection is deterministic, gallery comparison is ordinary repeated Context evaluation, and renderer-specific palettes are prohibited. Existing color Themes migrate as one replacement. New continuous scales, automatic dark-mode selection, inheritance, and arbitrary color expressions require a separate design decision.
