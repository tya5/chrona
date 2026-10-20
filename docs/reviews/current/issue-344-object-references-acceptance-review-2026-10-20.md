# Issue344 — Level1 object-reference slice

[Active scope, design and implementation plan](https://github.com/tya5/chrona/issues/344#issuecomment-6291962311).
The [reviewer acceptance](https://github.com/tya5/chrona/issues/344#issuecomment-6290785975)
is the authority for this slice; the wider ecosystem issue remains open.
Normative Specs06/07/17/60 were published in `08742fa44`, with the extension-owned
namespace correction `201a4afc7`, before the respective product code.
Corrected implementation: `518e27afb`.

| Literal active-slice criterion | Disposition | Evidence |
| --- | --- | --- |
| Synthetic plan: a valid reference passes; a missing target, a wrong target profile and a cardinality error each fail with a pointer through validate, schedule and render. | met locally; release pending | `test_object_reference_validation.py` checks actual profile/Core validation, scheduler and render source closure, including valid references and per-element pointers. `test_object_references.py` and `test_generic_profile_fields.py` cover compatible-profile disambiguation, missing/incompatible/ambiguous targets and unconstrained references; existing delivery-profile controls pass. |
| A column over a reference shows the target title, en-US and ja-JP. | met locally; release pending | `test_object_reference_projection.py`: actual SVG in both locales and ordinary/lane tables; ordered many titles, source-local primary/Snapshot/scenario bindings, and no second entity-title lookup. English Style-encoding and Japanese lane-table SVG rasters inspected: titles visible without clipping. |
| Existing Projects unchanged (count table). | met on initial artifact; corrected-head confirmation pending | [Official50-slide count/byte audit](https://github.com/tya5/chrona/pull/1834#issuecomment-6292534493): all50 SVG and50 Scene bytes identical; only diagnostic-inventory source locations and two guard call sites change. No authored public-corpus changes. Final-head artifact must retain these payloads. |

Additional scope controls: scalar reference Style equality reads the resolved
title, not a raw-ID alias. Raw IDs remain encoding domains and legend identities;
same-title targets keep distinct keys/colours. Snapshot title renaming keeps one
identity, labelled from the first matched occurrence. Shared completion rejects
present non-scalars and cross-namespace/logical-Project aliases with existing
`E_PRESENTATION_SCALE_VALUE`; absent/null base paint remains unchanged.

Architecture review by root and two independent Luna reviewers: Core owns the
single immutable indexed target catalogue; effective profile metadata is detached
per source before presentation. Table and Style consume those facts. Layout,
Scene and adapters gain no resolver or geometry responsibility. No schema version,
derived expressions, default/inheritance evaluator, IDP diagnostic replacement or
project-specific conditional. The old opaque-list fact expectation now retains
bounded nonscalar state instead of masquerading as null.

The corrected extension owner normalizes reference profiles and namespaces for
both validation and binding descriptors. IDP actor entities remain authoritative
when an actor object shares the ID; same-named profiles owned by other packages
retain generic two-namespace semantics. The concrete validate-pass/projection-fail
case now passes actual SVG rendering. Independent Core/adapter review and40/44
focused tests pass (overlap); object-only assignees retain `IDP-PROFILE-003`.

Focused batches:166 tests across projection and adjacent Style/legend/formatting
integration, then12 final projection controls;52 model/generic/IDP tests and24
source-binding/parity/projection tests pass (overlap). Independent I2 focused
suite87 passes. No local full-suite/corpus sweep; CI supplies the disposable
public snapshot, full release matrix and materializer evidence. Final PR artifact
audit and exact-main three-OS release links must be added before slice acceptance.
