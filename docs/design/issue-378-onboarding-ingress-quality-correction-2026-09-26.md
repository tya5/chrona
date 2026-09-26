# Design Correction — Onboarding Ingress and Publication Quality (#378)

## Trigger and published facts

The #378 builtin preset implementation and initial derived-Theme Draft ingress
were published before their repository conformance gates passed. At
`fe1cb6fa`, the live checks identify an import cycle because the preset copy
use case imports `chrona.operational.resources.parse_document`, missing
author-facing annotations in the new preset-library and derived-Theme schemas,
an unclassified canonical Theme identity comparison, and stale generated CLI
and diagnostic inventories. These are release defects in the existing #378
slice, not reasons to weaken conformance.

## Ownership correction

The package preset catalogue is a presentation authoring input. Its use case
loads packaged bytes through `chrona.resources`, validates against the packaged
catalogue schema, and reports the existing builtin-preset diagnostic. It does
not depend on the operational workflow layer. Generic schema validation may
use the repository's schema diagnostic utility where needed, but cannot add a
reverse operational dependency. `chrona.resources` remains the authority for
packaged bytes and schemas; the use case owns the copy transaction.

Both new schemas are author-facing live contracts and therefore carry
descriptions at every authorable node and valid examples for every pattern.
The bounded Theme reference's source-byte and canonical effective identities
retain their separate semantics from the published identity correction.

The declared-value policy classifies the canonical effective-base comparison
as intentionally pinned, naming its producer. Generated CLI reference and
diagnostic inventory are refreshed by their owning tools after source changes.
The checks remain strict; no stale baseline or exclusion is introduced.

## Architecture result

Use cases may coordinate package resources and presentation contracts, but
must not import `chrona.operational`. This correction removes the concrete
cycle without duplicating an operational parser or moving presentation
vocabulary into operational command handling. It preserves the one-way
source → closure → Layout → Scene → adapter path and changes no materializer
semantics. The next Theme inheritance slice still resolves only at ingress.
