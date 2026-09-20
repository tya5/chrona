# Open Issue Remediation Plan — 2026-09-20

**Status:** Design and O2 published; O3 CLI implementation verified.
**Scope:** GitHub issues #19–#25.  
**User decisions:** describe the current alpha surface honestly; make Render Context the
only `render-review` entry because there are no compatibility consumers; preserve
specification numbers and add task-oriented navigation instead of renumbering.

## 1. Priority and dependency order

| Priority | Issues | Reason | Disposition |
|---|---|---|---|
| P0 | #20, #21 | Silent/traceback CLI failures and ignored required inputs make automation unsafe. | Define one diagnostic/exit contract and one Render Context entry, then implement first. |
| P1 | #23, #22, #24 | Package direction and presentation ownership are architectural invariants used by the P0 work. | Close design ownership before refactoring imports or adapters. |
| P2 | #19 | Release claims currently overstate user reachability. | Separate design/library evidence from product surface; do not add fourteen unrelated CLI features. |
| P3 | #25 | Navigation debt impedes readers but does not corrupt runtime results. | Preserve stable numbers, add grouped reading paths and vocabulary, archive the non-normative gate record. |

## 2. Normative design decisions

### D1 — CLI diagnostics and exits (#20)

All handled failures emit one JSON object with `status` and diagnostics using the
Specification 09 envelope. Project/input-semantic rejection returns 1; command syntax,
unreadable files, malformed YAML/JSON, and internal tooling failure return 2. A handled
failure never emits a Python traceback. `propose-set` replaces its positional JSON
literal with mutually exclusive `--value` and `--value-json` options.

`review` compares two immutable Project references from one declared local Store. Raw
working-tree paths are Drafts and are not accepted by this reproducible comparison verb.

### D2 — One review-render entry (#21)

`render-review` accepts a Render Context reference, snapshot root, Store identity, and
output path. It does not accept the former loose Project/Actual/View/Style/Theme/Profile
flags. Render Context v0.3 owns the current path: Project, View, Actual, one immutable
Presentation Preset, optional summary/detail profiles, target, and immutable resource
identities. The preset has the stable ID required by the reference contract and resolves
to complete Presentation Settings before rendering. The v0.1 token Theme, Style, and
Scene Profile stack is frozen legacy input and is not mixed into v0.3.

### D3 — Theme and Scene ownership (#22, #24)

Specification 07 is the sole v0.1 token Theme owner; its examples use the schema's
`values` plus `roles` syntax. Specification 29 owns the v0.2 resolved concrete theme in
Presentation Settings. The declared transition is token Theme → resolved concrete
theme → Scene-owned concrete paint; no renderer repairs or defaults it.

Specification 08 is the sole primitive, identity, and SceneDelta owner. Public v0.2
primitives are exactly `Rect`, `Text`, `Symbol`, and `Path`. Group, clip, region, slot,
table, axis, summary, and connector names are semantic `purpose`/metadata families, not
additional primitive kinds. `projectionInstanceId` identifies a projected instance;
`sceneId` adds its primitive-purpose suffix. Axis interval identity is source metadata,
not an alternative Scene identity. SceneDelta remains the interactive adapter contract
over these same primitives.

### D4 — Package direction (#23)

Specification 32 maps every Specification 09 component to a package. `core` imports
neither `storage` nor `extensions`; storage/application orchestration resolves extension
packages and injects their manifests into pure Core validation. Shared Theme helpers
move to the Scene paint owner so renderers never import private review helpers. A test
enforces forbidden package edges.

### D5 — Honest reachability and stable documentation (#19, #25)

The use-case catalog distinguishes design/library evidence from product surface. The
current alpha claim is limited to commands and documented entry points that actually
exist. Library-only successors remain implemented evidence, not user-reachable product
features.

Specification filenames/numbers remain stable. A grouped specification index supplies
Core, Presentation, Application, Successor, and Catalog reading paths. Concepts adds
the current presentation vocabulary. Pure process/gate material leaves the normative
specification directory; normative successor contracts remain even when milestone IDs
appear in their history.

## 3. Implementation phases

| Phase | Status | Contents | Acceptance |
|---|---|---|---|
| O1 — Design | Complete (`361c632`) | This plan plus Specifications 01, 07–09, 13–14, 27, 30, 32 and the grouped index. | Docs/schema references resolve; design is published before code. |
| O2 — Architecture | Complete (`0ac9a1e`) | Remove forbidden imports, centralize Theme helpers, add dependency test. | Full tests/conformance; no forbidden package edge. |
| O3 — CLI | Verified; publishing | Unified failures/exits, immutable review, Render Context v0.3 CLI, examples and tests. | CLI negative matrix, deterministic example output, full tests/conformance. |
| O4 — Contracts/docs | Pending | v0.3 schema/fixtures, Theme example validation, Scene contract test, navigation/archive cleanup, reachability evidence. | Every new schema fixture validates; links resolve; wheel smoke and CI pass. |

Each phase is one verified, non-forced commit published to `main`. If implementation
reveals an unmade semantic choice, implementation stops and the design correction is
published first.

## 4. Closure

After final CI succeeds, each issue receives a comment naming its design and
implementation commits plus verification evidence. Only fully satisfied issues are
closed. License selection remains outside this plan.
