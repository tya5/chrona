# Design Plan: Wheel Resource Topology and Evidence (#379, #381)

**Status:** Proposed

## Objective

Make each packaged resource have one authored source while proving that every
runtime resource tree is available from an installed wheel.  Remove the
HALCYON init-template duplicate and its synchronization gate; extend the
installed-wheel smoke through public commands that open the packaged icon and
raster-font byte paths.

## Verified starting point

- Hatch force-includes repository-root `schemas/` into
  `chrona/resources/schemas` in wheels.  `schema_resource()` prefers that
  wheel path and falls back to the development source authority.
- `src/chrona/resources/examples/halcyon-1/` is a byte-identical second copy
  of `examples/halcyon-1/`.  `tools/check_init_template.py` and conformance
  exist only to keep this copy synchronized.
- `initialize_project()` reads only the packaged duplicate, so an installed
  wheel works but a clean source authority cannot replace it without a resolver
  boundary.
- The installed-wheel smoke exercises schemas, the init template, and font
  metrics through SVG materialization.  It neither opens the bundled Material
  Symbols catalog under `resources/icons` nor causes PNG rendering to open
  bundled TTF bytes under `resources/fonts`.

## Design questions

1. Define a resource-location resolver that mirrors schema behavior for the
   init template while keeping `local_authoring` independent of wheel/source
   topology and never using a filesystem checkout-path fallback from a wheel.
2. Confirm the exact Hatch force-include mapping and source-development
   fallback work on editable source and isolated installed-wheel execution.
3. Define public-command wheel-smoke evidence for every resource tree, with
   output assertions that prove bytes were actually opened rather than merely
   listed.
4. Decide whether a resource-tree manifest or an explicit smoke matrix is the
   durable ownership boundary; avoid a broad directory scan that makes a new
   resource silently unowned.
5. Identify deletion scope: duplicated template tree, sync tool, conformance
   invocation, tests that assert the former topology, and documentation.
6. Review against resource ownership, installer isolation, init's
   non-overwrite/immutable-closure behavior, rendering boundaries, wheel size,
   and the existing CI sequence.

## Planned outputs

1. English design and whole-architecture review.
2. Implementation plan for resolver/packaging consolidation, smoke expansion,
   deletion, and release evidence.
3. Focused resolver/smoke tests, source and installed-wheel execution,
   full regression, public materializer checks, generated artifact review, and
   three-platform CI.

## Exit criteria

- HALCYON is authored once in `examples/` and is present in the wheel by an
  explicit build mapping.
- Source and installed wheel use the same resource resolver contract without
  fallback to an arbitrary checkout path.
- Installed-wheel smoke reaches schema, example, font-metric, font-byte, and
  icon resource trees through public behavior.
- No synchronization gate remains for a duplicate that no longer exists.
