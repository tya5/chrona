# Corpus policy

Chrona's public examples are a semantic-register corpus, not a collection of
interchangeable screenshots. Each project owns one register and its README
states what that register adds. Together the projects exercise Project, Actual,
Snapshot, and Extension contracts through declared, reproducible materializer
slides.

Extend an existing register when its semantics still fit; add a project only
when a new register is genuinely needed. A new public contract field ships in
the same release as an exhibiting declared resource and materialized slide.
Generated coverage is a curation backlog, not a conformance threshold: missing
coverage informs the next example without making ordinary user input invalid.

Every evidence artifact must be declared by `manifest.yaml` and reproduced by
the public materializer. Hand-authored previews, undeclared variant folders,
and duplicate semantic source files are not corpus evidence. See
[the generated coverage report](../examples/corpus-coverage.md) and
[Specification 32](../specification/32-repository-layout-and-packaging.md).

When a change affects presentation vocabulary, treatment, Layout composition,
or generated presentation artifacts, its acceptance review records the exact
regenerated corpus/gallery command and artifacts visually assessed by a
reviewer. This human record supplements — never replaces — byte reproduction,
schema validation, and generated-output checks. The capability disposition
matrix is generated from the typed ceiling; it is review evidence and never a
render input. Start from the
[visual acceptance record template](../reviews/presentation-visual-acceptance-record-template.md)
when the change has visual output.
