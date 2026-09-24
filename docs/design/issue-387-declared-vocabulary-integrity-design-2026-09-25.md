# Declared Vocabulary Integrity Design (#387)

**Decision:** Accepted.

## Scope

A published resource declaration must not promise a finite vocabulary that its
owner later rejects.  This design introduces a repository-quality inventory
and gate for that claim, then corrects the five known divergences at their
actual ownership boundaries.  It does not make the inventory a runtime
dependency and does not centralize unrelated Theme, Context, or View policy.

## 1. Authority and inventory

Each finite declared vocabulary has three distinct facts:

1. the schema path and declared set;
2. the product owner and its accepted set; and
3. an explicit disposition when the field is deliberately open-ended.

`tools/vocabulary_inventory.py` is a deterministic repository tool.  Its
checked-in report lists those facts for a bounded, version-pinned registry of
schema fields.  Its policy file names the owning module, the accepted values
or owner-local acceptance probe, and an `open-ended` reason where a static
finite comparison would be false.  `--check` fails if a listed finite declared
set is wider than its accepted set, if an owner/field has no classification,
or if the report is stale.

The tool is evidence, not product behavior.  Product validation remains at
resource loading or the boundary that has the concrete value.  This preserves
the existing direction:

```text
schema/resource -> owner-local normalization -> Layout -> completed Scene -> adapter
                      ^
              actionable diagnostic

repository inventory -> generated report / CI only
```

The diagnostic inventory from #371 remains a separate tool: it reports
literal diagnostic construction and public ingress reachability; it does not
know schema vocabulary or decide product acceptance.

## 2. Theme marker and pattern

Theme tokens are owned by Theme normalization, not by SVG serialization.
Until #384 changes their representation, the finite names are:

| token type | accepted names |
| --- | --- |
| `marker` | `triangle` |
| `pattern` | `outline`, `diagonal-hatch` |

Theme v0.6 declares those names at the token schema branch and loader
validation names the supported set.  This moves a wrong value from an adapter
failure to resource validation.  All current v0.5 Themes migrate in the same
atomic contract slice; no v0.5 reader is retained.

#384 is deliberately allowed to replace these scalar names with structured,
resolved geometry and a larger supported shape vocabulary.  When it does, it
changes the Theme contract and this inventory's owner probe together.  It must
not restore an adapter-owned lookup or add an unreviewed free string.

## 3. Context locale

Locale is Context-owned input because it affects normalized text before
Layout measurement.  The current product has corpus evidence for `en-US` and
`ja-JP`; no other locale has complete deterministic formatting.  Render
Context v0.15 therefore declares exactly those two locale tags.

Compact date formatting implements both tags without consulting host locale:
English retains its existing abbreviated-month representation and Japanese
uses a deterministic numeric `YYYY年M月D日` representation.  Axis formatting
already derives its language branch from the declared tag and remains within
the same closed pair.  A new locale is a design and contract extension across
all text formatting paths, not an arbitrary string accepted by one formatter.

All Contexts migrate atomically to v0.15.  There is no reader for v0.14.

## 4. View annotation anchor

The present Layout implementation resolves one semantic anchor type: an
object's planned/actual mark endpoint.  View v0.13 expresses exactly that:

- `anchor` is required for every View annotation;
- `kind` is the constant `object`;
- `id`, `facet`, and `endpoint` are required; and
- endpoint is one of `start`, `finish`, `at`, or `body`.

The richer relation/group/temporal proposal is not silently represented as
accepted syntax.  #386 owns any subsequent extension, including a decision
about Project-level annotations and the required resolver/geometry/evidence.
The new schema version is migrated across all Views in the same slice; no
compatibility reader makes a missing anchor mean something different.

## 5. Diagnostics

Schema validation produces the established structural diagnostics at the
resource boundary.  Owner-local checks that cannot be represented in JSON
Schema raise a stable diagnostic with the field path and admissible values.
Renderer adapters retain primitive-shape invariants only: they do not own
Theme or Context vocabulary checks.

The inventory records those diagnostics as evidence but does not prescribe
their rendering.  This avoids a second diagnostic authority and retains #371's
ingress/actionability policy.

## 6. Migration and generated evidence

Theme, View, and Context version changes are intentional clean contract
migrations.  All shipped resources, Context references, conformance fixtures,
schema registries, resource parsers, materializers, and public generated SVG
evidence move in their owning slices.  A public materializer must reproduce
every affected artifact after the migration; a generated diff is reviewed
before acceptance.

## Rejected alternatives

- **Leave unconstrained values and improve adapter errors.** It keeps a
  validating document invalid at render and leaves adapters interpreting
  authoring policy.
- **Use one global vocabulary registry at runtime.** It collapses unrelated
  Theme, Context, and View ownership into a new authority.
- **Narrow locale to only `en-US`.** It invalidates the declared Japanese
  corpus instead of completing the already-selected locale boundary.
- **Claim relation or temporal annotations now.** It treats a future feature
  as present behavior and defeats #386's design responsibility.
- **Keep old schema readers.** The product has no compatibility requirement;
  retaining them would hide the contract migration and multiply vocabulary
  authorities.

## Acceptance

- A generated declared-vocabulary report is deterministic, checked, and
  classifies every bounded field it inventories.
- No inventoried finite declaration is wider than its owning accepted set.
- Theme marker/pattern, Context locale, and View annotation anchors validate
  at their owning resource boundary before rendering.
- `en-US` and `ja-JP` output remains deterministic and public corpus materializers
  reproduce their declared Contexts.
- #384 can extend marker/pattern as a single Theme-to-Scene contract change,
  and #386 can extend annotations as a View-to-Layout contract change, without
  bypassing the gate.
