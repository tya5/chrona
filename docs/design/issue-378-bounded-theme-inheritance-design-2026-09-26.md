# Design — Bounded Theme Inheritance (#378 I378-2)

**Status:** Proposed for architecture review.

## Decision

I378-2 adds a derived **Theme** source form only.  It does not add View
inheritance.  A View combines selection, comparison, row construction,
windowing, visibility and content policy; no independent replacement surface
is presently safe to admit.  A derived View therefore remains a future,
separately designed resource rather than a generic document merge.

## Source form and resolution

A derived Theme is a `chrona/theme/v0.12` document with `id`, `kind`, and a
`body` containing exactly `extends` plus optional `values` and `roles` maps.
`extends` is a safe relative local path and the exact canonical
`contentIdentity` of the base Theme.  Its base must be an ordinary complete
Theme of the same kind.  Base resolution occurs in presentation ingress before
`parse_contract`; the resolver reads the base relative to the derived file,
rejects traversal, computes canonical identity, checks kind/version, and
detects cycles by resolved canonical path.

The resolver creates a detached ordinary v0.11 Theme: it deep-copies the base
`body`, overlays only supplied named entries in `values` and `roles`, preserves
all other envelope fields from the base, and assigns the derived source `id`.
The resulting complete document is schema-validated and parsed normally.
There is no recursive merge inside individual token or role values, no delete
operator, no override of `colorBindings`, and no inheritance interpreted by
Layout, Scene, or adapters.

## Identity and closure

The effective Theme has canonical identity of its resolved v0.11 document.
The derived source and its pinned base are retained as ingress provenance, but
the RenderClosure resource list and materialization input contain the effective
ordinary Theme only.  Thus existing Theme consumers keep their one-resource
contract and immutable contexts remain self-contained after resolution.

Draft ingress may resolve the local pair directly.  Immutable Context ingress
resolves only a derived Theme whose base is supplied by the same snapshot
reader and whose exact identity matches its declaration; it never walks a host
filesystem.

## Rejections

Stable errors distinguish unsafe path, absent base, base identity mismatch,
base kind/version mismatch, cycle, unknown derived key, invalid derived
override, and invalid effective Theme.  A derived document cannot be supplied
where a generic presentation resource is expected without this resolver.

## Five-line acceptance fixture

The tutorial fixture has a complete base Theme and a five-line derived Theme
that changes two existing named values.  It produces a visibly different Draft
while preserving all inherited Theme fields.  Unknown names are rejected: a
derived source may replace an existing base `values` or `roles` entry, not add
new vocabulary.

## Explicit non-goals

- View inheritance, arbitrary YAML merge, collection deletion, and implicit
  base discovery.
- Guided workspace override expansion.
- Layout/Scene/adapter-specific values or geometry in Theme inheritance.
- A new materializer closure grammar or a runtime inheritance edge after
  effective-resource resolution.
