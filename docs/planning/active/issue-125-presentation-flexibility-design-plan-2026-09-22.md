# Issue 125 Presentation Flexibility Design Plan

## Scope

Define deterministic graceful-degradation policy, bounded View-owned
per-object presentation intent, and a validated presentation extension
registration seam.  The work must preserve the existing boundary: View states
author intent, Layout selects and records feasible placement, Scene projects
completed placement, and renderers remain unaware of policy.

## Design questions

1. Specify a finite ordered fallback ladder and whether a suppression rung is
   valid for each content family.
2. Define View syntax and precedence for item/row intent without coordinates or
   layout profile mutation.
3. Define how Layout manifest records the selected rung and how public output
   tests expose it.
4. Decide the extension registration authority, schema validation boundary, and
   collision rules with built-in semantic/column names.

## Completion gate

Publish a design and whole-architecture review, then an implementation plan
with independent schema, policy/composer, extension, and acceptance slices.
