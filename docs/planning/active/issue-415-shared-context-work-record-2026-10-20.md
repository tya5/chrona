# Issue 415 — shared deck Context

Status: design plan; authoring boundary and migration allowance approved by
the [reviewer](https://github.com/tya5/chrona/issues/415#issuecomment-6280957121).
Selected syntax and the remaining contract still require review before code. Current scope:
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

## Design questions and whole-architecture review

1. Choose the smallest explicit deck-fragment/slide reference form. Reuse
   existing reference/address schemas; no templating language, directory scan,
   implicit defaults from another evaluation or unbounded include mechanism.
2. Close the allowed shared/override fields and precedence. Decide map versus
   whole-value replacement, arrays, omission and null before code; unknown and
   duplicate keys cannot become silent merge policy.
3. Specify immutable loading/bootstrap, cycles, missing files, Store identity,
   revision/hash verification and address bases for inherited references and
   Context-relative font assets. Sharing cannot weaken any pin or containment.
4. Approved boundary: one authoring expansion owner produces a fully explicit,
   pinned Context before copying/pinning/immutable closure; public entrypoints
   reuse it. Existing explicit Contexts remain byte-preserving. Scene provenance
   includes the exact Context contentIdentity; count migration-only provenance
   changes explicitly, never hide them in a comparison filter. Do not add a
   format-preserving YAML/CST layer just to freeze old source hashes.
5. Check normal Store rendering, materializer copying/repinning and Draft paths
   for one composition owner. No duplicate merge implementation in CLI, tools,
   renderer or adapters. Keep scheduling and geometry unaware of composition.
6. Review optional schema additions against Spec56 sections3.2/7 and shared
   parts/frozen definitions. Existing explicit Contexts keep their behavior;
   update normative authority before finalizing implementation planning.

## Publication slices and gates

1. Publish this plan. Complete selected YAML examples, normative contract and
   whole-architecture review; request reviewer approval on415 before code.
2. After approval, publish the implementation plan: exact owning files,
   schema/loader/materializer slices, migration handoff, focused tests and
   independently publishable boundaries. A discovered contract gap returns here.
3. Implement approved slices; test synthetic sharing/isolation, all failures,
   immutable reads and actual byte equivalence. Full schema equivalence and
   generated public evidence belong to the shared CI snapshot; no local full
   pytest duplicate or hand-authored generated outputs.
4. Land the feature and literal review, then coordinate the reviewer migration.
   Verify its same-cohort reduction and output table, and the review-containing
   exact-main three-OS release before closing. A pending migration keeps415 open.

Syntax, override/address rules and implementation decisions remain open until
reviewed. This branch is not a second active landing PR while1788 is in flight.
