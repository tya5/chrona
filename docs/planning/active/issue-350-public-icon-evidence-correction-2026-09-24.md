# Design Correction: Public Icon Authoring Evidence (#350)

**Status:** Design complete — implementation plan for I350R-6.

## Finding

The successor implementation is at `icon-catalog/v0.3`, but Specification 64
still labels the prior v0.2 proposal and the top-level authoring guide has no
icon catalog/import/View path. Controller Z proves a private regression slide,
not a user-followable reusable example. This leaves the public contract and
evidence behind the implemented architecture.

## Corrected public surface

R6 publishes one coherent author journey: import a local Iconify collection
with the public CLI; pin the resulting v0.3 catalog in a Context or pass it to
draft rendering; select direct and encoded visuals in View; materialize the
declared example. Documentation names only v0.3, canonical primitive streams,
and the closed SVG/PNG capability policy.

The corpus contains purpose-specific vector and raster assets plus reproducible
fixtures for bundled Material and user-imported Lucide/Tabler. It demonstrates
both leading and trailing text visuals, direct and encoding selection,
meaningful and decorative accessibility, and every target class through small
focused views—not one unreadable demonstration surface.

## Architecture consistency review

Examples remain ordinary pinned Context inputs and public materializer output;
they do not grant renderer filesystem lookup, raw SVG rendering, network
discovery, or author coordinates. Documentation refers to the same Context,
View, Theme, Layout, Scene, and adapter ownership specified in 64.

## Implementation and acceptance plan

1. Correct Specification 64 version/status and link its user commands from
   README and CLI help tests.
2. Add reusable imported-catalog and target-family examples, with only intended
   materialized SVG changes.
3. Add source/closure, schema-description, SVG accessibility/semantics, decoded
   PNG, and artifact-size evidence.
4. Publish an R350 requirement matrix mapping every R350 row to direct tests,
   fixture, and generated evidence; release review then performs R7 gates.
