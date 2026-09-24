# Issue 370 implementation plan — resolvability quality gates

**Status:** Approved for implementation

**Implements:** [Issue 370 design](../../design/issue-370-resolvability-quality-gates-design-2026-09-24.md)

## Delivery rule

Each slice publishes a complete report/tool/policy increment.  Generated
reports and policy records are committed in the same change as their extractor.
No slice adds a product-runtime dependency on `tools/` or conformance policy.
Before every push, fetch `origin/main`, verify the fast-forward relationship,
run the slice acceptance, and push serially.

## I370-1 — Diagnostic population and actionability gate

**Files/areas:** `tools/diagnostic_inventory.py` (new),
`conformance/resolvability-quality-policy-v0.1.yaml` (new),
`docs/diagnostics/inventory.md` (generated), focused tool tests,
`conformance/run_conformance.py`.

**Work:** Implement conservative AST extraction of literal diagnostic
constructions, stable source anchors, layer attribution, detail-bearing call
shapes, deterministic Markdown rendering, and `--check`.  Add exact per-code
bare-ingress classifications, with the report retaining every bare site.
Replace unjustified bare ingress exceptions with details owned by their
existing detecting boundary; a code is allowlisted only when its identifier is
the complete message across every bare ingress use.

**Acceptance:** the report is byte-current; a newly introduced bare ingress
construction and a stale/missing policy entry fail focused tests; an internal
identifier-only invariant remains reportable without being forced into a
user-facing message; conformance invokes the check.

## I370-2 — Declared-versus-computed inventory and producer closure

**Files/areas:** `tools/declared_value_inventory.py` (new), shared policy
loader/extraction helpers if justified, policy classifications, generated
`docs/diagnostics/declared-value-inventory.md`, focused tests,
`chrona identity bytes|document` CLI adapter/tests, and user guide.

**Work:** Implement conservative intra-function comparison extraction and
exact site classification.  Verify each `pinned-deliberately` producer against
the live argparse tree.  Classify product bookkeeping only with a concrete
resolver/refresh route.

**Resolved correction:** existing producer coverage was incomplete.  The
published identity-producer correction adds exact raw-byte and canonical-
document inspection commands while retaining the separate validated workspace
revision command.  Do not claim a generic hash command is equivalent to
canonical workspace identity.

**Acceptance:** every derived site is exactly once classified; stale/missing
records and nonexistent producer commands fail; report is current; public
producer tests prove emitted value equals the corresponding declared format.

## I370-3 — CLI documentation validity and fresh-project smoke

**Files/areas:** `tools/check_documented_commands.py` (new), policy command
surface classifications, focused parser/extractor tests, `README.md` and
guides for omissions, `tools/wheel_smoke.py`, CI invocation if needed.

**Work:** Extract documented invocations with location provenance, parse them
against live nested argparse metadata, and derive the reverse public command /
option population.  Document every intended author-facing command and option
or give it a narrow reviewed non-documentation reason.  Extend installed-wheel
smoke to execute the README's fresh `init` then `materialize` sequence in an
empty directory.

**Acceptance:** malformed command/flag/value, nested-command ambiguity,
undocumented public option, and stale policy cases fail focused tests; the
documented first-run sequence succeeds only after wheel installation and
creates its expected artifact.

## I370-4 — Corpus magnitude, release gate, and publication review

**Files/areas:** `tools/corpus_coverage.py`, its tests and generated report,
policy magnitude classifications, conformance wiring, release-review document.

**Work:** Extend the existing semantic corpus model with deterministic
magnitude facts and declared-limit qualification.  Add/adjust corpus fixtures
only where a published product limit lacks adequate semantic-scale evidence;
do not invent a Scene/SVG threshold.  Run all focused checks, conformance,
structural checks, full parallel pytest, public materializer byte checks,
generated SVG batch diff, installed-wheel smoke, and GitHub CI.

**Acceptance:** every declared limit has an explicit threshold and qualifying
corpus evidence; missing classification and insufficient scale fail focused
tests; all reports are current; release review maps every Issue 370 acceptance
item to direct evidence.

## Cross-slice constraints

- Share AST/policy helpers only after both tools prove the common abstraction;
  do not create a generic static-analysis framework prematurely.
- No compatibility policy version or broad grandfathering list is retained.
- A newly discovered diagnostic form, identity computation, public CLI form,
  or scale concept is a design deviation: update the design and architecture
  review, publish them, then resume the affected slice.
- Generated Markdown is reviewed as evidence, never consumed by Chrona
  runtime code.
