# Issue #50 closure-integrity design review

## Scope reviewed

`authored context → Revision Store reader → closure resolver → public materializer →
generated SVG evidence`, plus Scene measurement diagnostics and snapshot return shapes.

## Findings and disposition

| Boundary | Finding | Disposition |
| --- | --- | --- |
| Authored context | Materializer rewrites content identities before `LocalSnapshotReader` sees them. | Preserve original context bytes and validate pins before render. |
| Revision Store | Reader correctly validates a supplied pin; its validation is bypassed by rewriting. | Reuse the reader's identity diagnostic; do not add a second identity authority. |
| Font assets | Tool rewrites identities in parsed context metadata. | Verify copied packaged bytes against authored metadata without mutation. |
| Provenance | A re-dumped context is presented as an execution closure. | Make provenance a distinct derived artifact, never renderer input. |
| Scene | Required title measurement is subscripted directly. | Route every missing required measurement through the existing stable diagnostic. |
| Snapshot storage | Test treats a resource reference as a snapshot document. | Preserve distinct API contracts and correct the assertion. |
| Generated evidence | PR #51 contains only regenerated SVGs and is reproducible. | Merge as evidence-only; subsequent closure repair must re-run the gate. |

## Architecture result

The design retains one immutable-source authority: authored references and the Revision Store
reader. The materializer is a transport and evidence producer, not an identity repair layer.
It introduces no legacy presentation contract, renderer fallback, or hand-edit workflow.

## Design closure

- Authored closure ownership: closed.
- Validation-before-copy/render order: closed.
- Font-asset treatment: closed.
- Derived provenance boundary: closed.
- Scene diagnostic contract: closed.
- Snapshot return-shape contract: closed.
- Evidence gate requirements: closed.

The implementation plan may proceed.
