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
After normally merging Issue1397 and its trusted derived tip `358cda0fd`,
the vocabulary/network integration batch passes31 tests.
Schema equivalence passes:1 added schema,39 unchanged;577 documents/467 mapped/
5 known invalid and739 unchanged probes; the post-merge rerun takes40.1s
for L2+L3. Schema inventory,
annotations/references, reachability, Theme consumers, text encoding and inward
import checks pass. Built wheel resource/schema bytes match their source files.
A fresh final-source wheel installed in an isolated venv imports from
site-packages, loads all117 bindings through the unchanged read API, and runs
`chrona --version`; its vocabulary identity is
`sha256:7fbb34ad6c0eb98ce3f6fe78dbef5cf44a4fdf99d54c1816457711ac7a31ff88`.
Independent installed-wheel checks confirm typed contract parsing, raw-byte
identity refusal and all19 public registry helper signatures unchanged.

Independent review corrected a mutable derived index; the import-direction
gate found a bootstrap diagnostic-layer cycle. The published correction keeps
native schema failures below rich ingress diagnostics; immutable indexes and
the inward-dependency gate now pass. No Python fallback table remains.

Official artifact after the reviewer correction: head
`ee9cbb3db` [snapshot39046678234](https://github.com/tya5/chrona/actions/runs/39046678234),
artifact12105913414 (manifest SHA256
`aabe3dcd291de83d72fe147cb4af13ebbd5f22cfd7a644ab600eb8a32ac7a60f`),
has109 unchanged paths: all50 SVG byte-identical; all50 Scene JSONs differ only
by one exact vocabulary provenance resource. No primitive, purpose, role,
geometry, paint, route or label changed. Two of9 reports change (source-line
inventory2551→2551bytes and diagnostics304701→305877); other7 are identical.

The preceding run39042795786 had13 pytest failures:11 expected-byte/fixture failures and two
schema index omissions; conformance, reproduction and MCP passed. Seven
affected Controller fixtures were refreshed through the standard materializer:
each SVG is byte-identical, each Scene differs only by the same provenance
entry. Three synthetic Scene characterizations now retain full-byte hashes and
assert the vocabulary identity; SVG hashes remain unchanged. Schema README and
the fixed host-ID accounting are corrected. Unrelated older Aster/capabilities
fixture differences were not absorbed. No product behavior or test comparison
was weakened, and no public examples/bot-owned output was edited.
The corrected focused batch passes39 characterization/materializer tests;
schema identifier/part accounting passes141 tests, covering all13 CI failures.

Corrected-head run39044257405 passes all three pytest shards, conformance,
reproduction, MCP and derived preview. Only derived-ready rejects the advanced
main after reviewer PR1669; there is no remaining failing product test. All52
changed artifact payloads match the prior artifact byte-for-byte. After merging
trusted-ready main `8c8a1e55b`, the vocabulary/closure/Editorial integration
batch passes29 tests. Current-base CI, reviewer PR acceptance and exact-main
three-OS release remain required. Parent419 remains open for S1/S2/C1.

Reviewer approval requires keeping the original rationale at the new authority.
All66 original comment lines across34 binding/group associations are preserved
verbatim in YAML, including issue references. The117 parsed values/order retain
digest `dca7540d246009b957bdb1dd4c8abecbb5a97174a594f1af48475cee0fbd97a8`.
The raw identity above includes those comments. Seven fixture pairs were
regenerated together with the standard materializer: SVG unchanged and Scene
only the vocabulary identity changed. For all three synthetic characterizations,
restoring only that old identity reproduces the preceding full-Scene SHA;
their SVG hashes remain unchanged. A fresh wheel installed outside the checkout
loads the new exact resource identity, all117 bindings and CLI version output.
No schema member was added for rationale. The official artifact above verifies
the corrected raw identity; its run predates the later main advance and does
not establish final-base CI success. Main `e71c8de3d` (Issue1660 and its trusted
derived evidence) is normally merged before the next final V1 push.
The post-merge vocabulary/closure, all-point folded-row and Editorial deadline
integration batch passes37 tests on this base.
The post-correction broad focused batch passes85 cases; seven public-example
checks still read unsynchronized committed Scenes locally and require the CI
derived snapshot. No public generated file was patched to satisfy them.
