# M7 Command-Closure Remediation Plan

**Status:** Complete — 2026-09-19

## Finding and correction

M7 requires a View-local annotation editor, but the Command Model described annotation commands only narratively. The closed v0.1 request registry and schema omitted their types, targets, and payloads. The schema also omitted the registered `unresolveActualObservation` payload and incorrectly constrained Store-issued revision tokens to Git syntax. Implementing an editor against those omissions would make the adapter a source of command semantics.

The Command Model, request schema, and positive fixtures now close all three gaps. Annotation commands use a View target and complete annotation intent; they cannot carry Scene geometry or Project mutation. `baseRevision` is an opaque non-empty Store token.

## Implementation authorization

M7 may now implement View-local annotation commands only through this request contract and a revision-bound View store. Scene coordinates, title matching, and direct Project mutation remain unauthorized.
