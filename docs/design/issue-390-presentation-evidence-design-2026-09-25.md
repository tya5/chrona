# Design: Presentation evidence and inspection boundary (#390)

**Status:** Accepted for implementation planning.

## Decision

#390 adds three complementary quality instruments.  None is a renderer, a
second schema validator, or an aesthetic pass/fail oracle.

1. A structural Scene-delivery check inspects every public dataclass in
   `presentation.scene.model`.
2. A generated prior-art disposition matrix joins #391's closed capability rows
   with a small, curated set of reference systems.
3. A visual acceptance record binds a reviewed generated gallery batch to a
   presentation change.

## All-Scene delivery check

Each public Scene-model field has one declared delivery class:

* `adapter-consumed`: at least one renderer or public artifact consumer reads
  it;
* `inspection-consumed`: it is serialized into the schema-validated public
  inspection Scene and has a named inspection/tool consumer; or
* `derived-only`: it is an internal component of another public Scene value and
  must be read by its parent serializer/consumer.

The check parses the model and presentation consumer ASTs.  It compares every
dataclass field with a finite checked-in ownership manifest that names its
delivery class and reason.  A field absent from the manifest, a stale manifest
entry, or a field with no allowed consumer fails.  The manifest is not an
allowlist: a `derived-only` or `inspection-consumed` field still needs a
verifiable consumer.  This preserves legitimate Scene inspection evidence
without pretending every fact must become SVG markup.

## Prior-art disposition matrix

`docs/research/presentation/` will own a generated/checked matrix.  Its rows
are imported from #391's capability registry; it cannot invent a capability
row.  Columns contain only durable reference categories and source links,
initially Chrona, external editorial Gantt reference, Mermaid, and Microsoft
Project.  Each Chrona row records `supported`, `deferred`, or
`deliberately-rejected`, with its owner/reason and link to the responsible
design/issue.

The matrix is review evidence, not a feature-ranking table and not a promise to
copy another product.  Reference facts are refreshed from primary sources when
the matrix changes.  A missing reference observation is `unknown`, never
silently interpreted as absence.

## Visual acceptance record

A presentation-changing implementation adds one current review document that
records: the generated gallery/corpus command and input commit, artifact set,
reviewer, observed intended differences, accessibility/semantic distinction
check, and any non-goal.  The record is required by implementation plans and
acceptance reviews; it does not block unrelated semantic changes and is not
machine-scored for visual taste.

`tools/render_design_gallery.py --check` remains deterministic generated-output
evidence.  The human record confirms that a reviewer actually assessed the
same committed output, rather than replacing byte checks with screenshots or
subjective golden images.

## Boundaries and acceptance

The check must not import producer/runtime modules or parse SVG.  The matrix
must not supply runtime configuration.  The review record must not alter a
gallery catalogue or suppress diagnostics.  I390 accepts only when the check,
matrix validation, focused negative fixtures, generated documentation checks,
and a real presentation-change review record all pass.
