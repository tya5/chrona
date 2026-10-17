# Issue419 — semantic resource acceptance

<!-- chrona:literal-acceptance/v1 -->

V1 implementation `2f7045611` follows the approved design in PR1664,
published implementation plan `94a6abddd` and architecture correction
`04e092df5`. [Current work record](../../planning/active/issue-419-semantic-resource-work-record-2026-10-17.md).
V1 is partial delivery; no parent closure is claimed.

## Literal issue acceptance

### Issue #419

- Source: [issue and consolidated433](https://github.com/tya5/chrona/issues/419)
- Observed: 2026-10-17

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | The semantic vocabulary is a versioned resource with a schema. | met | [Resource](../../../src/chrona/resources/semantic-vocabulary.yaml), [schema](../../../schemas/semantic-vocabulary-v0.1.schema.yaml), immutable loader and [117-value/negative tests](../../../tests/unit/chrona/presentation/test_semantic_vocabulary.py). Official release gates remain pending. | — |
| 2 | A design set can introduce a visual distinction the product did not anticipate, without a code change. | not met | [S1/S2 remain planned](../../planning/active/issue-419-semantic-resource-work-record-2026-10-17.md#architecture-review-and-proposed-implementation-sequence); externalizing the host vocabulary alone does not implement authored Style rules. | — |
| 3 | The presentation coverage report derives distinctions from resources rather than from source. | not met | Style/coverage work remains; [dev B may start C1 independently through the unchanged registry read API](https://github.com/tya5/chrona/issues/419#issuecomment-6235010287). | — |
| 4 | No field in the registry is unread. | met | All six existing mapping values retain their [recorded consumers](../../planning/active/issue-419-semantic-resource-work-record-2026-10-17.md#v1-equivalence-inventory-117-entry-baseline); registry/Scene/contrast/reachability tests pass. The independent117-row digest proves no value was dropped. [Closure tests](../../../tests/unit/chrona/presentation/model/test_semantic_vocabulary_closure.py) prove explicit vocabulary identity, normal/Draft consumption and rejection of forged/missing inputs before Scene. | — |
| 5 | The report lists every purpose drawn in the corpus with its realized role count, generated from committed Scenes. | not met | The [current report](../../gallery/semantic-realization-coverage.md) still needs C1's derived population. | — |
| 6 | Adding a purpose to the semantic registry without a classification fails the check. | not met | [Current classifications](../../../src/chrona/presentation/model/semantic_realization.py) still need C1's population gate; V1 does not invent metadata. | — |
| 7 | The 31-of-40 figure, or its successor, is visible in a committed, checked document. | not met | C1 must publish the current derived fraction in the [checked report](../../gallery/semantic-realization-coverage.md); the historical number is not current evidence. | — |

## Programme-level criteria (optional)

Focused batches pass92 resource/closure/registry/Scene cases and52 diagnostic/
boundary/docs cases (overlap); the final direct-type-import batch passes47.
Schema equivalence passes:1 added schema,39 unchanged;577 documents/467 mapped/
5 known invalid and739 unchanged probes; L2+L3=36.5s. Schema inventory,
annotations/references, reachability, Theme consumers, text encoding and inward
import checks pass. Built wheel resource/schema bytes match their source files.
A fresh final-source wheel installed in an isolated venv imports from
site-packages, loads all117 bindings through the unchanged read API, and runs
`chrona --version`; its vocabulary identity is
`sha256:c302c329c8fa1d34b983fd2c1badd479cbd54a3a423b290b32b2e06d67ea606d`.

Independent review corrected a mutable derived index; the import-direction
gate found a bootstrap diagnostic-layer cycle. The published correction keeps
native schema failures below rich ingress diagnostics; immutable indexes and
the inward-dependency gate now pass. No Python fallback table remains.

Official materializer counts, unchanged SVG/primitive geometry/paint evidence,
the intended Scene resource-provenance additions, reviewer PR acceptance and
exact-main three-OS release are pending. Parent419 remains open for S1/S2/C1.
No examples or generated artifacts were edited.
