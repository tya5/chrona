# Issue 134 Hyperlinks Design Plan

## Verified starting point

* Project v0.3 object/entity schemas have no typed link and are immutable.
* View v0.5 has no `visibility.links` and is immutable.
* `ReviewItem` already provides object provenance to Scene primitives; SVG is
  serializer-only and currently emits no wrapper primitive.

## Design questions

1. Define a typed Link value and URL policy: accepted absolute schemes,
   declared relative/wiki form, optional accessible title, normalization, and
   rejection diagnostics. Free-form fields are not an alternate ingress.
2. Decide scope precisely: object links must reach the selected object title
   and row primitives; entity links may only ship if a typed entity-backed
   projection subject exists. Do not imply entity links merely because the
   Project schema can store them.
3. Define `visibility.links: none | title | row` ownership and exact primitive
   selection. `title` means the table cell whose source is the selected row
   subject; `row` means primitives carrying that primary item/source identity,
   excluding unrelated group/axis/annotation decorations.
4. Define the immutable migration: Project v0.4 and View v0.6 plus all public
   resources, context references, schema inventory and tests change atomically.
5. Define renderer policy: Scene receives a completed `href`/link title;
   SVG wraps only the emitted element in escaped `<a href>` with an accessible
   title. Typst/TikZ/PDF stay deterministic and inert; no renderer infers or
   validates a link.

## Architecture review required

The design must prove:

```
Project typed link + View intent -> Projection selection -> Scene primitive
attribute -> declared renderer serialization
```

Project owns link fact, View owns visibility, Scene owns selected primitive
metadata, and renderer owns target syntax. Layout must not use link data for
geometry; a renderer must not read Project/View resources or retry selection.

## Implementation and evidence plan

Publish design and implementation slices for (1) typed Project/View contracts,
(2) projection/Scene selection, (3) SVG serialization and target invariance,
then run schema/closure, focused object/title/row fixtures, public materializer
checks, generated SVG diff review, and full pytest before closing #134.
