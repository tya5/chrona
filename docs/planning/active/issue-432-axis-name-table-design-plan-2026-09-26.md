# Design Plan — Independent Axis Name Tables (#432)

**Published base:** `a6fad8406f8b46f32a41044d72b09df64fc1b939` on
`origin/main` (2026-09-26). **Issue:** [#432](https://github.com/tya5/chrona/issues/432).
The local `.venv311/` is untracked and is not source evidence. Issue #462 is
awaiting an owner update and is outside this plan.

## Published facts and unresolved facts

- #408's [design](../../design/issues-405-406-407-408-400-axis-and-visible-failure-design-2026-09-25.md)
  requires a finite name table selected independently of the form. Its
  [acceptance review](../../reviews/current/issues-405-406-407-408-400-axis-layout-acceptance-review-2026-09-25.md)
  accepted the per-tier schema, but the author-reachable cross-language
  rendering criterion was not evidenced.
- The live View is v0.21. A labels tier carries a finite `form` or auto
  `forms`; `AxisLabelIntent` carries no table identity. `Layout` formats both
  fitting candidates and final text, and `axis.py` branches on the first
  language subtag of the Render Context locale. English months are constants;
  Japanese forms collapse to two outputs. No Scene or adapter owns this choice.
- #432 has no comments as observed on 2026-09-26. Its proposal is a lead, not
  a replacement for the repository's architecture and normative contracts.
- The exact published corpus contexts, schema migration scope, and any
  namespace for author-supplied tables still require an implementation audit.

## Literal issue acceptance

1. Under `ja-JP`, a month tier can render `Jan`, `January`, `1月` and `01`; under `en-US` it can render `1月`.
2. No two distinct month forms produce the same string under the same table without that being reported.
3. No axis label path branches on a language code.

## Use cases and design questions

The primary use case is a bilingual review whose document locale and axis
vocabulary differ. The same selected table must govern candidate-fit
measurement and final placed text, including automatic tiers. An author must
be able to choose all four January forms above without a host-locale override.

Resolve these before product code:

1. Where are finite built-in name tables declared, versioned, validated and
   made extensible? Is the public identity a table ID, a locale tag, or a
   resource reference? Can a View select one without adding locale semantics
   to Project or adapters?
2. How do `short-month`, `long-month`, numeric and year-bearing forms compose
   table data so all forms are observably distinct? How are year, half,
   quarter, week and day labels covered without a language branch?
3. Is equivalence invalid at resource closure, or reported per requested
   tier/form? What diagnostic identifies table and colliding forms? How is
   automatic candidate selection affected?
4. What migration keeps the 21 public materializers deterministic? If clean
   form semantics change existing Japanese output, record the deliberate
   incompatibility and regenerate evidence atomically; do not retain a hidden
   locale compatibility branch.

## Design slices and review gates

1. **Contract and model:** compare #408, View, Render Context, resource and
   diagnostic specifications. Select one explicit table identity and finite
   form semantics. Specify defaults, validation, extension and migration.
2. **Architecture review:** trace View/resource selection through normalized
   intent and Layout measurement to completed Scene text. Check adjacent
   calendar, fiscal, font, automatic-axis and package designs. Update living
   specifications or an ADR for changed public semantics. Publish the design
   and independent review before finalizing implementation planning.
3. **Implementation plan:** identify atomic schema/resource migrations, code
   owners, tests and public artifacts, each with a reviewable publication
   boundary. Publish before changing product code.
4. **Implementation and release:** execute only approved slices. Focused
   negative/positive tests must cover the literal acceptance matrix, auto
   fitting and all affected labels. Run conformance and public materializer
   byte checks locally; inspect generated Scene/SVG in one batch. Use the
   three-OS CI matrix for full pytest, wheel and newest-Python reproduction.

## Expected evidence

- A table/form matrix for January under both document locales, including
  the five cross-language cases in acceptance item 1.
- A deliberate duplicate-form fixture whose result is an explicit diagnostic
  or a documented equivalence record; no silent collapse.
- A structural check that the axis label path contains no language-code
  branch and that Scene/adapters never format a date.
- A corpus migration inventory, generated Scene/SVG diff review, focused
  tests, conformance, CI links, and an acceptance review with each literal
  criterion and its direct evidence.
