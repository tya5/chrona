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

## Boundaries

Examples do not select product policy by project, manifest, or slide identity.
The inventory is a documentation and quality gate; it does not validate
Project/Presentation resources a second time, generate Scene data, or change
renderer behavior.
