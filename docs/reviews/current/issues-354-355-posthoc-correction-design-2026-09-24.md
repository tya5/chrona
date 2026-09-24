# Issues #354 and #355 — Post-hoc Correction Design

**Decision:** Accepted correction to the accepted #354 and #355 designs.

## Trigger and scope

The closure review found two implementation omissions: #354 did not enforce
its one-axis collection contract, and #355 omitted the promised finite-schema
vocabulary inventory.  This correction makes those promises executable before
another gallery set is admitted.  It also records, without solving in this
slice, the independently discovered Layout/Theme token-coupling product debt.

## #354: executable one-axis contract

For every comparison set, the inventory validator compares the four pinned
presentation reference identities (`view`, `theme`, `colorScheme`, `layout`).
It uses this closed ownership map:

| Dimension | Owning references |
| --- | --- |
| `content` | `view` |
| `composition` | `layout` |
| `visual-grammar` | `view` |
| `appearance` | `theme`, `colorScheme` |

At least one owning reference must differ across peers.  A peer may differ in
no reference outside that owner set plus its declared `comparison.supports`.
`supports` is an ordered, duplicate-free list from `layout` and `theme`; it is
available only to a `content` set, and records a typed prerequisite rather
than another dimension.  A changed non-owner/non-support reference raises
`E_DESIGN_GALLERY_AXIS_LEAK:<set>:<reference>`.

This validates resource identity, not the semantic sub-selection inside a
View.  `content` and `visual-grammar` both have View ownership under
Specification 55; the catalogue's closed dimension/axis metadata remains the
documentary statement distinguishing those subdomains.

`halcyon-two-surfaces` must no longer rely on an undisclosed Theme/Scheme
difference.  Its dependency-network context is re-pinned to the programme
board's wallboard Theme and control-room-dark Scheme while retaining its
network View and Layout.  If that declared context cannot materialize, the
entire set returns to `deferred`; it must never be published as a multi-axis
comparison.

Deferred records describe proposals only.  Their `dimension` is optional:
when present it is one of the closed gallery dimensions; when absent the
proposal is explicitly outside Design Space.  The print/typeset proposal
therefore omits `dimension` rather than misclassifying target selection as
Content.

Generated set pages continue to show the normalized reference diff.  When a
peer pair differs in exactly one reference, the page additionally embeds the
normalized unified YAML diff of that referenced resource.  The gallery README
and every set page name `tools/render_design_gallery.py` and its regeneration
command.

## #355: bounded vocabulary backlog

The report retains explicit semantic-register probes and adds a second,
non-normative vocabulary inventory over exactly the schemas owning the four
declared corpus resource families: Project, Actual Set, Snapshot Reference,
and Profile Package.  The schema selection is explicit and version-pinned in
the tool; it does not scan all repository schemas or mistake tool-internal
contracts for corpus vocabulary.

The inventory traverses only direct object/property and array-item paths,
including finite branches under schema combinators.  It emits each
`enum`/`const` value in lexical schema/path/value order with the declared
resource paths exercising it, or `—` when uncovered.  Open maps, prose, and
non-direct conditional inference are excluded.  An explicit uncovered section
is calculated from this matrix.  The output is a curation backlog only and
does not create a coverage threshold or renderer dependency.

The negative-lag predicate is defined once, rather than constructed with an
intermediate placeholder.

## Product finding: portable Layout tokens

Halcyon Layout resources refer to Theme token names (`spacing.*`, and, for
some layouts, `panel.*`).  This prevents a View/Layout comparison from keeping
Appearance fixed, independently of table feasibility.  A successor issue must
decide whether Layout declares a required portable token vocabulary that every
Theme supplies, or declares defaults for the tokens it introduces.  It must
also separately address the existing table-overflow feasibility constraint.
This correction neither adds defaults nor weakens Theme validation.

## Architecture review

The validator and report remain maintainer-only documentation tools: no import
edge reaches resolution, Layout, Scene, materialization, or public CLI.  The
gallery still consumes committed SVG evidence downstream.  Strict reference
closure makes Specification 55's Design Space boundary observable without
turning a gallery assertion into a renderer policy.  The vocabulary inventory
reads schemas and declared examples only, preserving schema authority and the
one-way corpus-to-documentation flow.
