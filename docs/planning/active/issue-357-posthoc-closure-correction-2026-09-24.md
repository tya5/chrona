# Issue #357 — Post-hoc Closure Correction

## Trigger

The post-hoc review of `2e8f3b3` confirms the catalog-neutral performance
design and its release gates, but identifies one source-compatibility
regression and two missing invariants in the acceptance suite.

## Decision

`chrona.resources.safe_load` remains the sole shared YAML/JSON ingress. A
leading `{` is only a JSON fast-path hint: if `json.loads` rejects it, the
codec must retry the safe YAML loader. This preserves deterministic JSON
catalog performance while accepting every YAML flow mapping accepted before
#357.

Catalog closure remains catalog-neutral. Its ingress validates every icon and
alias key shape, and now also requires every `entryAliases` target to name a
canonical icon. Full entry schema validation and compact-path expansion occur
only for View-selected canonical entries. An unselected malformed entry must
not block closure; a selected malformed entry must fail as
`E_ICON_CATALOG_SCHEMA` at its icon pointer.

The importer intentionally writes canonical JSON despite the conventional
`.yaml` output name: JSON is a YAML subset. User-facing documentation must
state this explicitly. The older projection proposal is already marked
superseded and remains only as an audit record.

## Architecture review

| Boundary | Responsibility after correction | Prohibited behaviour |
| --- | --- | --- |
| Resources codec | Prefer JSON only when valid; otherwise safely load YAML. | Format detection that rejects legal YAML. |
| Catalog envelope | Validate global shape and alias referential integrity. | Expanding all vector geometry. |
| Closure selection | Validate and expand selected entries only. | Silently accepting a selected malformed entry. |
| Importer/docs | Emit deterministic JSON and describe it as YAML-compatible. | A package-specific or second reader path. |

## Acceptance

- A top-level YAML flow mapping is accepted through every migrated codec path.
- A malformed unselected icon leaves a render that selects another icon valid.
- A malformed selected icon fails with `E_ICON_CATALOG_SCHEMA` and its
  `/body/icons/<name>` source reference.
- An alias whose target is absent fails catalog ingress.
- README and Specification 64 state that imported `.yaml` catalogs contain
  canonical JSON, a YAML subset.
