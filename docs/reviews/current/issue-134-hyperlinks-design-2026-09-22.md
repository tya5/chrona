# Issue 134 Typed Hyperlinks Design

## Contract

Project v0.4 adds optional object `link`. It is either an absolute URL string
or `{href, title?}`. `href` accepts `https`, `http`, and `mailto` absolute
URLs, or a wiki-relative path beginning `./` or `/`; fragments and JavaScript,
data, protocol-relative, and unqualified forms are rejected. `title` is
plain accessible text, not markup. `link` is not admitted through `fields`.

Entity links are deliberately out of scope: the current review surface has no
entity-backed primitive identity, so accepting an entity link would publish a
fact with no defined consumer. A future entity surface may add it under its
own design.

View v0.6 adds `visibility.links: none | title | row`, defaulting to `none`.
`title` selects only a selected primary object's table cell whose declared
column source is `title`. `row` selects that object's primary marks, table
cells and plot labels. Neither mode selects relation paths, groups, axis,
legend, notes, annotations, Snapshot/Actual comparison primitives, or a
different object's source occurrence.

## Ownership and data path

Projection carries the validated object link as a typed optional fact. View
normalization turns the mode and selected View columns into immutable link
selection facts. Scene uses completed primitive source/provenance and that
selection to add `href` and link title to `ScenePrimitive`; Layout does not
see link data. No primitive kind or semantic registry entry is added.

```
Project link -> ReviewItem -> View-normalized selection -> ScenePrimitive
    -> SVG <a> serialization
```

SVG escapes attributes and wraps exactly one emitted primitive with
`<a href="…" target="_top">`; optional title is serialized as accessible
wrapper metadata. Typst and TikZ retain their existing bytes because they
ignore the optional primitive metadata. Renderers never access Project or
View resources.

## Immutable migration

Project v0.3 becomes Project v0.4 and View v0.5 becomes View v0.6 in separate
but ordered atomic public-contract slices. Each moves schema identity,
contract registry, inventory/README, all current resources/context references,
profile requirements, validation fixtures and tests. No v0.3/v0.5 compatibility
parser is retained.

## Architecture consistency review

The design retains Project ownership of semantic link facts, View ownership of
whether a link is shown, Scene ownership of primitive metadata, and renderer
ownership of syntax. It introduces no coordinate, styling, scheduling, routing,
or target fallback behavior. `none` keeps existing evidence artifacts
byte-identical even when Project links exist.

## Acceptance evidence

* Project URL/schema/closure rejection cases and object projection tests;
* a title-mode fixture with exactly one wrapper per linked selected row;
* a row-mode fixture proving selected primary-only provenance;
* escaped href/title serialization and Typst/TikZ invariance;
* all existing public materializers and generated SVGs unchanged under `none`.
