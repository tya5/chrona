# Issue 806 — inline typed fields

## Baseline and scope

Selected design; no product implementation. Published planning base is ready main
`bd6898017e3314bcfaffa3432d977d9a0f00fdd2`.
[Owner decision](https://github.com/tya5/chrona/issues/806#issuecomment-6255826606)
supersedes the old deferral: implement option B, not an overlay. Authority:
[Spec 65](../../specification/65-terse-plan-syntax.md),
[148 design §5.2](../../design/issue-148-terse-draft-syntax-design-2026-10-01.md),
[typed-fields guide](../../guides/typed-fields.md), Project/profile contracts,
and the shared extension validator introduced by 1682.

Dev A owns this item. Started 1754 landed through PR 1769 at `3fba1804d`;
full trial acceptance depends on B's 1755. Return to
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

## Selected design and whole-architecture review

The selected behavior is specified once in [Spec 65 §12](../../specification/65-terse-plan-syntax.md#12-inline-typed-fields-and-declared-profiles-806).
This explicitly supersedes 148's deferral/string-only option B; the overlay
remains deferred. Package declarations and object profile selection are
necessary to fulfill compile-time typed validation, not another configuration
or transient catalogue.

Independent review identified four necessary closures, now incorporated:
validate every explicit profile binding (including fieldless objects); use
one acquired package-byte snapshot for validation and temporary staging;
permit assignment-specific quoted values without weakening other lexical
separators; resolve file-output packages at the intended Project directory
and make stdout relocation obligations explicit.

Architecture checks against Specs 05/56/65, Project/profile schemas, the
shared extension resolver, emitter/importer, CLI dispatch and import-direction
guard:

| Boundary | Decision |
| --- | --- |
| Syntax vs Project semantics | Pure terse produces existing Project declarations and transient explicit-profile bindings. Shared validators retain all package/field rules; ordinary YAML types stay open. |
| Resource resolution | Application-only one-read byte snapshot; shared containment/identity logic; no I/O in terse. Direct render stages validated bytes, not a second source read. |
| Positions and errors | Existing escaped-pointer source map, one complete assignment span; same field codes. Authored extension schema findings remain user errors, not compiler defects. |
| Determinism/migration | No schema bump/new dependency/reserved object names. No defaults or host metadata in YAML; old no-clause plans stay byte-identical. |
| Presentation/storage | No View/Theme/Layout/Scene behavior or Store contract changes. Typed render consumes exactly the same Project/package bytes as YAML. |

No owner decision remains open. Before product code, finalize and publish
the implementation slices and evidence gates below. No product code has
changed.

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

Selected design and normative Spec 65 are ready for publication after the
independent architecture check above. Implementation planning is not final;
no product code has changed.
