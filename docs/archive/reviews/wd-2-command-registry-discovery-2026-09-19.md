# WD-2 Command Registry Discovery Review

**Date:** 2026-09-19  
**Disposition:** Fail — WD-2 is split; implementation remains frozen.

## Evidence

- `src/chrona/commands/commands.py` and `src/chrona/app/cli.py` execute a project typed-field
  mutation through `set_typed_field` / `execute_set_typed_field`.
- `10-command-model.md` identifies `setTypedField` as a project structure/field
  command family.
- Its closed v0.1 serialized registry and
  `command-request-v0.1.schema.yaml` omit `setTypedField`.

## Consequence

An AI proposal cannot safely wrap an unspecified project Command without creating a
second, unvalidated vocabulary. WD-2 therefore has two mandatory closure steps:

1. WD-2a adds the canonical project-field Command contract and fixtures.
2. WD-2b adds the AI proposal and authorization contract restricted to that registered
   vocabulary.

No M3, M5, or M9 acceptance claim may use the current direct helper as evidence of a
serialized Command contract until WD-2a is closed.
