# Architecture Review: Published Inspection Scene (#385)

**Decision:** Accepted.

| Boundary | Decision | Result |
| --- | --- | --- |
| Layout -> Scene | Layout supplies all table, text, route, and mark geometry once. | Accepted; typed columns close the only identified structural discard. |
| Scene -> target adapter | Adapter serializes completed primitives only. | Preserved. |
| Scene -> inspection serializer | Explicit typed projection with schema validation. | Accepted; no dataclass reflection or policy recomputation. |
| closure -> Scene asset evidence | Raster uses pinned content identity, not embedded bytes or a host path. | Accepted. |
| Scene -> external adapter | Consumer declares supported completed capabilities outside Chrona's runtime. | Accepted; no premature plugin registry. |
| Scene -> authoring | One-way inspection artifact; Command/revision authority remains unchanged. | Accepted. |

The design removes the inactive `PresentationScene` aggregate instead of
letting it compete with the live `SceneSurface` route.  `InspectionScene` is
created exactly where a completed surface becomes available, and the target
adapter and inspection serializer are sibling consumers.  This preserves the
Project -> View -> Theme -> Layout -> Scene responsibility chain established
by the placement refactor.

The review also confirms that Scene capability names denote completed feature
data.  They do not grant an external consumer authority over Theme resolution
or turn the existing target-profile resolver into a plugin mechanism.  The
contract is intentionally inspectable and version-pinnable, not geometry
stable across future Layout revisions.

No scheduling, Project schema, materializer authority, or renderer ownership
changes.  #375 may read the serialized inspection artifact; #383 and #142 may
prove separate consumers later, but neither enters the #385 runtime path.
