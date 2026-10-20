# Issue 415 — shared deck Context

Status: design approved; final implementation plan published before product code.
Authoring boundary and migration allowance approved by
the [reviewer](https://github.com/tya5/chrona/issues/415#issuecomment-6280957121).
The [selected contract is approved as written](https://github.com/tya5/chrona/issues/415#issuecomment-6282070481). Current scope:
[issue and reviewer assignment](https://github.com/tya5/chrona/issues/415#issuecomment-6280175603).

## Published baseline

- Inspected ready main `671e08086d516077fa7fb640e6c0b8978fa2daa5`:
  Render Context v0.17 requires explicit project, view, theme, colorScheme,
  layout, inputs, environment and target. There is no shared-Context edge.
  Later reviewer1787 changes only preset wording, not this contract.
- `RenderContextContract`, `resolve_render_context` and the materializer own
  typed loading, immutable reference resolution and portable closure copying.
  Specs 09/13/15/56 govern identity, Store containment and schema additions;
  View/Theme/Layout/Scene/adapter ownership must remain unchanged.
- HALCYON currently has 19 Context files, 2,587 non-empty lines, measured with
  `rg --files examples/halcyon-1/contexts` and `awk 'NF {n++} END {print n}'`.
  The issue's eleven-file/1,228-line figures are historical, not today's count.
  The migration review must name the same manifest cohort before and after.
- No old local work or inherited implementation is counted as complete.

## Literal acceptance and ownership

| Source | Literal criterion | Required evidence / owner |
| --- | --- | --- |
| Issue | A deck declares its shared presentation once, and a slide states only what differs. | Authorable deck/slide YAML, synthetic contract and render tests. |
| Issue | Changing the theme of an eleven-slide deck is one edit. | Multi-slide fixture; one shared change reaches all intended slides without changing unrelated decks. |
| Issue | The corpus decks are expressed this way, and their rendered output is unchanged. | Reviewer-owned migration; 0 SVG/geometry/paint/diagnostic changes. Reviewer explicitly permits counted Context-provenance-only Scene changes. |
| Reviewer 1 | A deck file plus slides that state only their differences render byte-identically to today's fully explicit Contexts (synthetic test). | Compare fully resolved inputs, actual output and provenance explicitly; do not silently exclude changed fields. |
| Reviewer 2 | Override precedence and an unknown or duplicate key are pointed diagnostics. | Positive precedence and negative unknown/duplicate/invalid-reference cases with source pointers. |
| Reviewer 3 | Measured on HALCYON-1: the reduction in Context lines once the reviewer migrates the examples, and the count table (expected 0 output changes). | Same-cohort line counts and per-slide output counts, with the approved Context-provenance-only allowance stated separately; reviewer owns migration, dev verifies acceptance. |

## Selected design and whole-architecture review

Canonical contract: [Specification 40 section 7](../../specification/40-example-reproducibility-and-materialization.md#7-shared-deck-context-authoring-415).
The existing manifest `context` is already an explicit-file fallback; do not
overload it. Add inline `contextDefaults` (a body fragment) and slide
`contextOverrides: {id: ..., body: ...}`. This needs no fragment resource kind,
include graph or additional path base. Resource references remain atomic.

The finite `inputs`/`environment` map overlays are necessary, not a general
deep-merge facility: all19 HALCYON Contexts share the Project and Actual refs;
14 share fontMetrics, but there are6 viewports and2 locales. Whole-environment
replacement would retain the largest font-copy duplication. Arrays and all
other objects replace whole; explicit null removes a member, and complete
Context validation still rejects missing required members.

| Authority / boundary | Consistency decision |
| --- | --- |
| Specs09/14 application entrypoints | One authoring composer reused by materialize CLI/library/tool; immutable render-review remains unchanged. Draft is not given an implicit deck lookup. |
| Specs13/15 immutable identity | Expand before copying/pinning/closure. Pin the expanded bytes at an owned transient address, never the fragment's hash/address. Preserve every surviving resource pin and Store boundary. |
| Specs40/50 materializer integrity | Explicit sources keep exact raw bytes. Composed source staging cannot collide with authored resources; no author files or pins are rewritten. |
| Existing deck consumers | Initialization, derived Scene provenance, corpus/presentation coverage and design purity reuse the selected explicit source, not a guessed file path or a second merge. Provider deferral remains slide-aware and cannot delete an authored file at a virtual address. |
| Spec56 schema/diagnostics | Formalize the existing materializer manifest contract in `schemas/example-materializer-v0.1.schema.yaml`, adding optional authoring properties in place. Reuse live Context property definitions; reject unknown/duplicate keys with exact origins. No canonical Context schema widening is needed. |
| View/Theme/Layout/Scene/adapters | Receive only the same explicit evaluated inputs. No new scheduling, geometry, routing, paint or adapter policy. |

Intentional admission change: previously ignored unknown/duplicate manifest
keys, YAML mapping merges and cyclic aliases are rejected, not compatibility
behavior to retain. Valid explicit manifests and Context bytes remain unchanged.
Ordinary YAML serialization is sufficient; the approved migration allowance
covers counted Context-provenance-only Scene changes, not geometry or ink.

Review decision: Spec40 section7 is approved as written, including syntax,
finite merge/null rules, origins, owned staging and every consumer connection.
There are no open design decisions; immutable render-review remains explicit.

## Publication slices and gates

1. Publish selected design, Specs09/13/40/50 consistency changes and request
   reviewer approval before code. The current design is not final implementation
   approval.
2. After approval, finalize/publish the implementation plan: authoring schema
   and pure composition with synthetic precedence/null/isolation/pointed-error
   tests; one materializer/copy-source integration and real explicit/composed
   SVG/Scene equivalence; then reviewer migration. One feature PR may carry
   these source commits; no extra paperwork-only landing cycles.
3. Implement approved slices; test synthetic sharing/isolation, all failures,
   immutable reads and actual byte equivalence. Full schema equivalence and
   generated public evidence belong to the shared CI snapshot; no local full
   pytest duplicate or hand-authored generated outputs.
4. Land the feature and literal review, then coordinate the reviewer migration.
   Verify its same-cohort reduction and output table, and the review-containing
   exact-main three-OS release before closing. A pending migration keeps415 open.

Readiness audit scope (all consume one selected-source record, not private merges):

| Consumers | Required connection |
| --- | --- |
| `usecases/materialize.py`, `usecases/local_authoring.py` | Explicit/composed bytes, owned address, normal closure copying and provider deferral. |
| `tools/check_draft_viewport_matrix.py`, `check_theme_role_consumers.py` | Enumerate manifest-selected bodies rather than globbing Context files. |
| `tools/corpus_coverage.py`, `presentation_coverage.py`, `check_design_purity.py`, `check_example_reachability.py` | Inspect completed refs with the manifest-root base; preserve source reachability without false orphans. |
| `tools/example_inventory.py`, `render_design_gallery.py` | Completed body and honest explicit-file or manifest/slide source links. |
| `tools/derived_evidence.py`, `presentation_font_identity.py`, `tests/support/public_evidence.py` and their callers | Replace mandatory Context-path assumptions with source provenance plus completed mapping/bytes; preserve exact identity/font checks. |

Their adapters and synthetic twins belong to the feature before corpus migration;
do not defer them until migrated examples break. Admission/composition is one
application owner; inspections do not need a staged file. Require a manifest ID
only for composition, preserving valid explicit-only no-ID manifests.
Pointed failures reuse the application failure-report transport; strict loading
must detect duplicate/merge keys and cycles before ordinary loading loses them.

## Final implementation plan

Public base: `f567d692202f19dda8bbb0b3ecc424968584a931` (design in PR1797;
archive-only PR1799 does not change the approved contract).
`resolve_deck_context(manifest_path, slide_id)` is the single selection owner.
Its immutable selected-source record carries completed `document`, exact
`payload`, owned `address`, optional explicit `source_path`, manifest/slide
provenance and origin pointers. Manifest enumeration reuses the same admission
and selector; inspectors never create temporary Context files. The existing
Path-based copier delegates to a payload-based internal seam so explicit callers
remain byte-preserving. Authoring failures use existing `StableFailure`
code/message/sourceRef transport; no new diagnostic envelope is necessary.
Line/range data may be retained internally, but is not a new public contract.

Parallel ownership: composer/schema/unit tests; materializer/init/integration;
inspection tools and their tests. The coordinator owns integration, publication
and review. Source changes follow this plan's verified remote commit, not a
private working copy. The one feature PR follows all three source slices.

| Slice | Owned files and acceptance | Focused verification |
| --- | --- | --- |
| Authoring resolution | An application-owned `usecases/deck_context.py` and `schemas/example-materializer-v0.1.schema.yaml`: strict admission, one selected-source record (bytes/body/address/origins), finite composition, explicit-byte preservation. No immutable Context widening. | New `test_deck_context.py`: precedence/null/isolation, eleven-slide shared edit, conditional manifest ID, unknown/duplicate/merge/cyclic-key pointers, atomic reference/array replacement and missing completed fields; schema equivalence. |
| Closure and consumers | `usecases/materialize.py`, `local_authoring.py` and the complete consumer table above reuse that record. Check staging collisions before writes; retain normal pins, root bases, provider deferral and actual source links. CLI/tool keep shared typed failure transport. | Existing materializer, init/provider, failure-transport and each affected tool's unit modules; composed-source twins for enumeration/provenance/font/reachability; mismatched pin, collision and provider-negative tests. |
| Acceptance and publication | One feature PR carries the separately reviewable source commits, specification and literal review; no authored generated output. Reviewer corpus migration is a subsequent publication and keeps415 open meanwhile. | Synthetic explicit/composed real Context/SVG/Scene equality; actual CLI and standalone pointed failures; CI's one generated snapshot, full matrix/wheel/newest materializers. After reviewer migration: all19 same-cohort line/output table, inspected adapter output and exact review-containing main release. |

Publish and verify this final plan before product edits. Pause and correct the
design first if integration exposes a contract gap. Reviewer-owned corpus
migration follows the feature; it is not silently counted as feature evidence.
