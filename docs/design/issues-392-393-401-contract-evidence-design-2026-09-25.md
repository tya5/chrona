# Contract evidence and semantic registry integrity (#392, #393, #401)

## Decision

Presentation coverage is a schema-driven observation of the current public
contracts.  Semantic-registry integrity is a structural property of the
Layout-to-Scene implementation.  Locale remains a finite Render Context
contract, presently `en-US` and `ja-JP`.

## Ownership

| Concern | Owner | Explicit non-owner |
| --- | --- | --- |
| Declared finite vocabulary | versioned schema | corpus and renderer |
| Declared-value realization report | coverage tool and generated report | hand-maintained inventories |
| Semantic-purpose identity | semantic registry | scene-id prefixes or Theme role overrides |
| Binding lookup reachability | structural test over presentation modules | corpus coverage |
| Locale admission | Render Context v0.15 schema/normalization | host locale and Layout fallback |

The coverage collector follows schema composition (`$ref`, object properties,
array items, maps, unions, and conditionals) until it reaches every finite
`const`/`enum` value.  It records a stable schema path and value.  A corpus may
leave a value unrealized; that is useful evidence, not an invalid document.
Consequently the collector cannot contain Theme-specific knowledge or a fixed
maximum path depth.

The registry remains the sole introduction point for a Scene semantic.  Every
binding must be looked up from Layout or Scene production code.  The gate
deliberately excludes the registry's declaration and test fixtures, and it
does not claim that a reachable binding has gallery evidence.  Those are two
different questions.

Annotation text resolves `annotationText` at the construction site.  Its
semantic purpose is therefore `annotation-text`; the annotation decoration
continues to use the distinct `annotation` binding.  Theme roles remain style
selection and may not repair a wrong semantic purpose.

## Locale closure

Render Context v0.15 is the public ingress and declares `en-US` and `ja-JP`.
Both formatter families are deterministic and reject any other locale before
rendering.  Superseded v0.12--v0.14 schemas are historical contracts and are
not silently mutated.  CLI help exposes the same closed vocabulary.  A third
locale requires a separately designed packaged formatting-data boundary; this
work neither introduces a process-locale dependency nor a partial table
architecture.

## Architecture review

This preserves Specification 32's authority chain: schemas normalize public
input, Layout composes completed placement semantics, Scene projects them, and
adapters serialize them.  It satisfies Specification 63's finite capability
ceiling without making the corpus an authority over admissible values.  It
also supports Specification 64's icon closure: `iconMark` is structurally
reachable now, while its corpus realization is independently reported and is
completed by the mark-composition program.  No font measurement, routing,
geometry, or target-specific behavior moves across a layer boundary.

## Consequences

* Adding an enum anywhere under a live presentation schema changes coverage
  output without a collector edit.
* A stale semantic binding fails a focused structural test before it can be
  misclassified as merely missing gallery evidence.
* #401 is accepted through conformance evidence, not duplicate code changes.
