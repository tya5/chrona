# Issue 806 — inline typed fields

## Baseline and scope

Design planning only; no product implementation. Public base is ready main
`bd6898017e3314bcfaffa3432d977d9a0f00fdd2`.
[Owner decision](https://github.com/tya5/chrona/issues/806#issuecomment-6255826606)
supersedes the old deferral: implement option B, not an overlay. Authority:
[Spec 65](../../specification/65-terse-plan-syntax.md),
[148 design §5.2](../../design/issue-148-terse-draft-syntax-design-2026-10-01.md),
[typed-fields guide](../../guides/typed-fields.md), Project/profile contracts,
and the shared extension validator introduced by 1682.

Dev A owns this item. Started 1754 remains in PR 1769: its CI/output audit
continues separately; full trial acceptance depends on B's 1755. Return to
1754 immediately for actionable failures. Do not take B's forecast/locale work.

Published facts: terse kinds are task/gate/group, the compiler emits neither
fields nor extensions, and compile has no profile-selection flag. The generic
validator selects declared profiles by Project object type and resolves their
packages through Project extensions. Therefore accepting arbitrary fields
without a persisted profile declaration would silently bypass the requested
typed validation. Existing token ranges and the single pointer source map can
position field findings; a second source map is unnecessary.

## Literal acceptance

| # | Literal owner criterion | Required evidence |
| ---: | --- | --- |
| 1 | A terse plan with `risk=high` on tasks compiles to a Project whose objects carry the field, and renders coloured by risk through the typed-fields guide's encoding. | Compile and render an actual typed-profile fixture; compare emitted fields and inspected SVG/Scene risk encoding. |
| 2 | An unknown key, a wrong type and an out-of-enum value each fail at compile with the line and column. | Shared-validator codes and exact key/value token ranges; no partial output. |
| 3 | Existing terse plans compile byte-identically. | All existing golden bytes, hash-seed/locale tests, parser/fuzz and importer regressions. |
| 4 | The terse guide documents the clause, checked by the docs tests. | Executable documented typed compile/render example and positioned error examples; generated CLI reference if the CLI changes. |

## Design questions to settle before code

- How the terse source declares an existing profile package and selects an
  object's profile while keeping task/gate/group schedule intent distinct.
  Persist the same extensions/type/fields as YAML; do not validate against a
  transient catalogue that disappears from the output.
- Scalar spelling: string-only option B from 148 versus typed scalar literals;
  quoting, duplicate keys, clause order, key alphabet and null/boolean/number
  handling must be explicit. Never import YAML's implicit scalar coercion.
- Pure parser/compiler versus application resource resolution: one shared
  validator, one source map, pointed package failures, no profile semantics
  duplicated in the parser. Unknown explicit profile selections must not
  silently become undeclared free-label types.
- Resource origin for file/stdin compilation, output relocation and direct
  `.chrona` render/validate/schedule. The current temporary Project directory
  loses relative profile paths; resolve this at the application boundary,
  without teaching presentation/storage about terse syntax or changing the
  emitted Project behind the author's back.
- Additive grammar without reserving previously valid object names; no
  `--with`, overlay files, new source maps, presentation syntax, schema bump,
  filesystem reads in `chrona.terse`, or source paths/hashes in emitted YAML.

## Design review and publication order

1. Publish this design plan.
2. Select the smallest complete declaration/typing/resource-origin contract;
   update Spec 65 and the 148 design's obsolete scope statements. Review against
   Specs 02/05/56, extension resolution, CLI dispatch, typed-fields validation,
   deterministic emitter/importer and dependency-direction checks. Publish.
3. Finalize an implementation plan here: parser/source ranges/emitter; shared
   validation and dispatch; docs and literal acceptance. Name tests and files
   for each slice, then publish before product edits.
4. Implement approved slices with synthetic focused tests in this worktree's
   venv. Batch actual adapter evidence; no corpus-specific conditions. CI owns
   full shards/materializers and the three-OS release.
5. Publish one implementation PR and concise four-row acceptance review. Close
   only after every literal row and review-containing exact-main release pass.

No selected design or implementation plan is final yet. Profile declaration,
scalar semantics and temporary-resource origin remain unverified decisions,
not assumed features.
