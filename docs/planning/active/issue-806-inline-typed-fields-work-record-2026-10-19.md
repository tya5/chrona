# Issue 806 — inline typed fields

## Baseline and scope

Implemented candidate; PR/release verification pending. Published planning base is ready main
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

Selected design, normative Spec 65 and architecture review were published at
`4294e23d8`; implementation plan at `1c745b453`, before product code.

## Implementation plan

One implementation PR, keeping the following source commits independently
reviewable. No new schema, dependency, overlay or public materializer input.

| Slice / owner | Files and connection | Acceptance and focused evidence |
| --- | --- | --- |
| S1 pure syntax / delegated | `terse/{lexer,parser,compiler,emitter,diagnostics,ledger}.py`; unit terse tests and negative fixtures. CompileResult adds explicit-profile object identities, not another source map. | Declarations, contextual profile, scalar assignments and escaped pointer spans follow Spec 65 §12. Legacy goldens unchanged; quote boundaries, duplicate/empty/nonfinite values, null/number round trips, kind/parent semantics, reserved-name and deterministic/fuzz tests. Compiler-owned new syntax codes receive negative fixtures; application-only unknown-profile code is tested with its package context. |
| S2 resources and application / dev A | `extensions/profiles.py`, `usecases/terse_compile.py`, `app/cli.py`; extension and CLI integration tests. Expose typed local package snapshots containing declared relative path, raw bytes and decoded manifest; keep the existing manifest-only resolver as a projection over that acquisition. PlanCompilation carries successful snapshots for staging. `compile_plan` accepts explicit optional resource origin; typed plans without one reject rather than implicitly reading cwd. | Shared containment/identity/manifest/field checks stay authoritative. Fieldless unknown profiles and invalid/ambiguous packages reject with positions; authored extension-schema errors are input errors. Compile stdout/file/stdin origins, no partial output, output refusal, required fields, wrong type/enum/key, source mutation after validation, exact-byte staging and cleanup on success/failure. Existing validate/schedule/render and table importer remain valid. |
| S3 docs and visual evidence / dev A | Terse guide/card and typed-fields guide; executable docs file markers/commands, CLI and render tests; concise literal review under `docs/reviews/current/`. | Reuse the typed-fields guide's package/encoding in an executable staged example. Actual SVG risk paint and Scene fields; direct terse SVG/Scene equal compile-then-YAML. Keep the one-page card and legacy examples. Run documented-plan/command checks and import-direction tests. |

S1 and the shared snapshot helper may proceed in parallel only after this
plan is published; S2 integration consumes S1's explicit binding identities
and existing single source map. Keep all syntax work in `chrona.terse`, all
package semantics in the shared validator, all file context/staging in the
application. If a contract gap appears, amend/publish design before code.

Verification batches: terse unit suite (including legacy bytes and seeded
fuzz), compile CLI and terse dispatch tests, extension/profile validation,
table import regressions, import-direction guards, and executable docs. Batch
SVG/Scene inspection with the typed render tests. CI supplies full pytest
shards, conformance and newest-Python public materializers; inspect the one
official derived snapshot for unintended changes, never edit generated public
outputs. After landing, require the review-containing exact-main three-OS
full release and a met row for each of the four literal criteria before close.

Publish S1/S2/S3 code and tests coherently, then acceptance evidence. Follow
the next ready main by a normal merge before the final PR push; coordinate
the actual landing on 1718. Archive completed 1702 records in the next docs
batch, not by moving main during another session's reservation.

## Candidate evidence

Shared snapshots `c276703a5`, syntax `60c4398a4`, application/CLI `ccda7bb51`,
docs and actual SVG/Scene encoding tests `1a02e5837`. Normally merged ready
main `137eed375`; no overwritten remote changes. Independent architecture
review found no contract gap. Snapshot origin/staging, package ambiguity,
fieldless bindings, required/unknown/type/enum errors, unchanged old bytes,
group rollup/parent semantics and import boundaries have focused coverage.
Latest-ready combined focused batch: 494 tests passed (terse, typed application,
CLI dispatch, extension/profile checks, table import, docs and import-direction
guards); closed-issue specification ledger: 3 passed. Documented-command check
passed; all seven typed-guide commands executed in the disposable workspace.
See the [literal review](../../reviews/current/issue-806-inline-typed-fields-acceptance-review-2026-10-19.md)
for actual raster and release gates; local success does not close the issue.
