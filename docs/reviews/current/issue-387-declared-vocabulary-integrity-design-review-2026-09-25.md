# Architecture Review: Declared Vocabulary Integrity (#387)

**Decision:** Accepted.

## Reviewed boundaries

| Boundary | Decision | Result |
| --- | --- | --- |
| Schema -> resource contract | Versioned finite vocabulary belongs in the owning schema. | Accepted. |
| Theme -> Scene | Theme values are checked before Scene; adapter does not select a marker/pattern vocabulary. | Accepted; #384 extends this boundary. |
| Context -> normalized content | Locale is closed before text measurement, so Layout does not discover unsupported locale values. | Accepted. |
| View -> Layout | View describes only anchor forms Layout resolves. | Accepted; #386 is the extension owner. |
| Scene -> adapter | Scene holds completed policy; adapter retains only primitive integrity checks. | Accepted. |
| repository tools -> runtime | Vocabulary inventory is generated CI evidence, never imported by product modules. | Accepted. |
| #371 diagnostics -> #387 | Diagnostic site/actionability inventory and vocabulary truth are complementary, separate contracts. | Accepted. |

## Findings

The current SVG adapter rejects marker/pattern names after Scene construction,
and annotation Layout rejects schema-admitted shapes after View validation.
Those are violations of the authority flow, not merely poor messages.  The
accepted design corrects them at Theme, Context, and View resource boundaries.

The review rejects adding a generic runtime vocabulary registry because it
would become a competing policy authority.  The generated inventory instead
has a deliberately narrow quality role: it detects that a schema's finite set
and its identified owner no longer agree.

The review also rejects treating the current two locale paths as a host-locale
feature.  Locale is declared Context data and must result in deterministic
text before font measurement.  The closed `en-US` / `ja-JP` contract is
therefore architecturally consistent with immutable materialization.

## Whole-system consistency

No Core scheduling or Project semantics change.  No renderer receives Theme,
View, Context, or inventory input.  Layout continues to own geometry and
routes; Scene continues to own completed primitives; adapters serialize those
primitives.  The contract migrations are intentionally non-compatible and
must update every declared corpus closure atomically.
