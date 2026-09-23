# Design Correction: Bundled Material Catalog Size (#350)

**Status:** Complete — implementation may resume at I350R-3 after this
correction and its architecture review are published.

## Observed deviation

The real Material Symbols Outline Rounded selection contains 2,336 canonical
Iconify entries.  Lowering its path geometry into the v0.2 renderer-neutral
command form produces a 17,924,767-byte YAML catalog (1,277,609 bytes with
gzip -9).  The earlier design deliberately left the exact artifact bound to a
release gate, but did not make the cost of normalized quadratic geometry
explicit.  Treating an informal source-package-size estimate as the catalog
bound would either make a required default impossible or pressure the design
to reintroduce raw SVG at runtime.

## Corrected decision

The default remains the complete fixed Material Symbols Outline Rounded
selection, not a silent curated reduction.  It is generated only by the local
importer from `@iconify-json/material-symbols@1.2.93`; the generated manifest
records all 2,336 canonical names.  The package ships the normalized YAML,
its complete Apache-2.0 notice, and the generator — never the npm archive or
raw XML.

The product bound is now explicit:

| Artifact | Maximum | Why |
| --- | ---: | --- |
| canonical YAML | 18,000,000 bytes | prevents accidental unbounded corpus/package growth while retaining the required complete variant |
| gzip -9 canonical YAML | 1,500,000 bytes | bounds distributable wheel contribution independent of filesystem compression |
| manifest entries | 2,336 | prevents a version update from silently changing the product default |

The release test must verify all three, the package resource load, source
identity, aliases `material` and `material-symbols`, SPDX/notice presence, and
the generated catalog contract.  A future compact binary catalog is a new
contract design: it cannot be substituted inside v0.2 because Context identity
and ordinary YAML materialization must continue to close exact catalog bytes.

## Whole-architecture review

This correction preserves the established authority chain.  The importer still
ends before Context closure; Layout, Scene, and adapters receive only typed
normalized entries.  It does not add filesystem discovery, runtime decompression
semantics, a renderer-specific path representation, or a compatibility reader.
The manifest is packaging provenance, not an authoring input; user-owned
catalogs continue to be ordinary v0.2 YAML documents and use the same closure.
