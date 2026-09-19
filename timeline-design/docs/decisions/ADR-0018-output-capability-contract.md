# ADR-0018: Output targets declare capabilities and fidelity loss

**Status:** Accepted  
**Date:** 2026-09-19

## Decision

Chrona treats every output as a Scene adapter governed by an explicit capability
profile and output manifest. Required semantic/accessibility distinctions either
survive or produce a stable diagnostic; release acceptance is mapped to the use-case
catalog. SVG remains the deterministic baseline and no output becomes canonical state.

## Consequences

New output types add adapter and fixture work but cannot silently degrade meaning or
create a renderer-specific semantic path.
