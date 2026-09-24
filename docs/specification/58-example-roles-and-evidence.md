# Example Roles and Evidence

**Status:** Accepted
**Depends on:** [38 Reproducible Example Closure](38-reproducible-example-closure.md),
[40 Example Reproducibility and Materialization](40-example-reproducibility-and-materialization.md),
and [12 Quality and Invariants](12-quality-and-invariants.md).
**Owns:** the separation of regression corpus, author curriculum, and gallery
evidence.

## Decision

One source tree may be referenced by three surfaces, but each surface has one
authority and one success criterion:

| Surface | Authority | Success criterion | Must not become |
| --- | --- | --- | --- |
| Regression corpus | `examples/*/manifest.yaml`, contexts, and committed generated SVG | Public materializer reproduces exact bytes and declared output properties | A tutorial or aesthetic catalogue |
| Curriculum | `docs/guides/` and small linked source fragments | An author can follow an ordered, truthful public command | A second resource format or an exhaustive gate |
| Gallery | `docs/gallery/` entries that reference a declared corpus slide | A reader can compare named output intents with source/provenance links | Hand-authored rendering evidence or a new runtime resolver |

Every corpus manifest declares a stable `role: regression-corpus` and every
slide declares a concise `evidence` statement.  The materializer verifies this
metadata and remains the only producer of committed generated SVG.  Curriculum
and gallery pages link to corpus resources; neither is discovered by test globs
or supplies an alternate materialization path.

## Inventory contract

A repository tool produces a deterministic inventory of live schema vocabulary,
declared corpus slides, curriculum links, and gallery links.  It diagnoses a
missing corpus role, duplicate slide identity, dangling documentation reference,
or gallery entry without provenance.  It reports coverage as evidence, never as
a requirement that a tutorial or one aesthetic gallery exercise every schema
value.

### Gallery design-catalog successor

The current `chrona/example-catalog/v0.1` is a flat provenance index.  A
gallery that compares reusable presentation designs requires a successor
catalogue contract, not additional fields whose meaning is inferred by the
renderer.  Its entries are documentary claims over one declared corpus slide
and its derived `PresentationDesignSummary`.

The successor entry has these finite categories:

| Category | Purpose | Authority |
| --- | --- | --- |
| Stable gallery identity and source | Names the entry and one `(corpus, slide)` pair. | Corpus manifest and slide identity |
| Editorial narrative | Gives title, intended audience, and the communication problem solved. | Gallery author; never evaluation input |
| Comparison declaration | Identifies a named paired-design set and the declared comparison axis. | Gallery author, verified against summaries where representable |
| Design assertions | States selected finite Design Space values expected from the derived summary. | Derived summary is authoritative; catalog claims must match it |
| Target/capability assertion | States the intended output target and only explicitly declared target capabilities. | Resolved immutable Context |
| Accessibility review note | Records human-readable rationale and any non-colour semantic distinction. | Gallery author, reviewed alongside rendered evidence |

The catalogue cannot contain Project facts, Actual observations, resolved
geometry, CSS/SVG snippets, renderer options, resource paths, package cache
locations, or a resource selector.  In particular, an accessibility note is
evidence narration; it cannot suppress an accessibility diagnostic or request
a renderer fallback.

Every paired set declares exactly one Design Space `dimension` from `content`,
`composition`, `visual-grammar`, or `appearance`, plus one shared human-readable
axis. All peers in that set use the same dimension and axis. Output target is
evidence metadata rather than a fifth Design Space dimension. A gallery page is
generated only from validated catalogue provenance, committed materializer SVG
evidence, and normalized presentation-reference diffs; it is documentation and
never a render input.

Catalog validation proceeds in this order:

```text
corpus slide identity
  -> materializer/Context provenance
  -> derived Design Space summary
  -> finite catalog assertion comparison
  -> documentary narration/link integrity
```

The validator diagnoses duplicate gallery identities, dangling corpus slides,
missing materializer provenance, a summary-identity mismatch, unsupported
assertion vocabulary, an unpaired comparison declaration, and an assertion
that disagrees with the derived summary.  A validation failure affects gallery
publication only.  It cannot alter rendering or make a corpus render consult
the catalogue.

### Paired design evidence

A gallery comparison is meaningful only when its peers declare the same
semantic Project/scheduling fixture and differ solely in ordinary presentation
resources and the resulting immutable Context.  The materializer evidence for
each peer remains independent and byte-pinned.  The gallery may explain the
visual difference, but it must not infer a semantic equivalence from matching
titles or Project IDs alone; the pair declaration is validated from the pinned
project/scheduling provenance.

Visual review images are derived inspection artifacts.  They may aid human
review but neither replace SVG byte evidence nor become package source.  A
gallery entry must explicitly state any target/capability and accessibility
limitation that matters to its claimed communication purpose.

## Boundaries

Examples do not select product policy by project, manifest, or slide identity.
The inventory is a documentation and quality gate; it does not validate
Project/Presentation resources a second time, generate Scene data, or change
renderer behavior.
