# Implementation Plan: Target Parts Catalogue (#718)

**Status:** Proposed. Depth C: no change under `src/` except packaged resources; no schema change.
**Base:** `main` at `4981db0a` (observed 2026-10-02).
Design plan: [issue-718-target-parts-catalogue-design-plan-2026-10-02.md](issue-718-target-parts-catalogue-design-plan-2026-10-02.md).
Design: [issue-718-target-parts-catalogue-design-2026-10-02.md](../../design/issue-718-target-parts-catalogue-design-2026-10-02.md).
Architecture review (conditions C1 to C3):
[issue-718-target-parts-catalogue-architecture-review-2026-10-02.md](../reviews/issue-718-target-parts-catalogue-architecture-review-2026-10-02.md).

## Acceptance map

| # | Literal acceptance | Evidence planned |
| ---: | --- | --- |
| 1 | a packaged catalogue contains every part in the table or lists why a part was dropped; passes the importer with no rejected element | slice S1: the catalogue, its importer run, the manifest inventory; dropped part (seigaiha) named with its reason in the design and the manifest |
| 2 | a gallery page (committed SVG and PNG) shows each part at two sizes and in two Themes | slice S2: `gallery.svg`, `gallery.png`, inspected as images |
| 3 | each target README records which of its parts are in the catalogue and which of #582 to #588 it still needs | slice S2: one section in each of 14 target READMEs and in the target B README |
| 4 | no file under `src/` other than packaged resources changes; no schema changes | `git diff --stat origin/main` over `src/` and `schemas/`, in the acceptance review |

The issue's rules (monochrome, fill or stroke, no literal colour or other forbidden construct, provenance and licence,
no effects) are checked by the importer and by the regeneration test; the acceptance review lists them as rows.

## Slices

### S1. The catalogue and its evidence (resources, tests)

Files (new): `src/chrona/resources/icons/chrona-target-parts-v2026-10.source.yaml`, `.yaml`, `.manifest`, and
`chrona-target-parts.NOTICE`. The source is the authored `theme-asset-source/v0.1` document with the complete MIT
notice; the catalogue is `chrona icon-catalog import --theme-assets` output, unedited; the manifest follows the
starter's (set, alias, SHA-256 of catalogue, source and notice, licence, entry inventory, densities) and adds a
`consumers` map that marks each frame and stamp entry `none-yet` with its owning issue (condition C1).

No existing test, tool or resource file is edited in S1. The wheel carries the four files by the existing package
rule; S1 proves it by building the wheel and listing it, and the new unit test reads them through the package
resource API (`builtin_preset_source_root("icons")`), as the library does.

Tests (new):

- `tests/unit/chrona/presentation/icons/test_packaged_target_parts_catalog.py`: manifest hashes, inventory and
  densities equal the files; the notice is byte-equal to the catalogue's notice; regenerating from the source gives the
  same bytes; every entry named in the manifest's `consumers` map exists; no entry is named in both families.
- `tests/integration/test_target_parts_theme_render.py` (condition C2): a Theme binding a catalogue glyph on
  `milestone-symbol` and a catalogue pattern on `axis-band-decoration2` renders through `chrona render` with the
  catalogue passed by `--icon-catalog`; the Scene holds a Symbol with the glyph's outline and a pattern with the
  tile, angle and density; every glyph and every pattern is accepted (parametrized over the manifest).

Generated evidence and checks: the importer reproduces the committed catalogue byte for byte; the wheel is built
and `tools/check_wheel_size.py` is run before and after (the numbers go into the acceptance review); the module
reachability and resource-list checks of conformance pass; no derived-evidence manifest changes.

Publication: one pull request, `Refs #718`. Independently publishable: yes.

### S2. Gallery and target READMEs (documentation, evidence)

Files (new): `docs/research/presentation/target-parts-catalogue-2026-10/` with `README.md` (what the catalogue is, how
to regenerate), `build_source.py` (the formulas that produced the source paths, kept as provenance), `render_gallery.py`,
`gallery.svg`, `gallery.png`.
Files (changed, appended section only): the 14 target `README.md` files and
`halcyon-1-target-design-2026-09-21/README.md`.

The gallery shows every glyph at 64 and 20 px and every pattern at 1x and 2x, each in two Themes (Hinoki and Night),
painted from token sets in the script; the geometry has no colour. The PNG comes from the pinned resvg route. Both
images are inspected, and the checked facts are recorded in the acceptance review. Each README section lists, from the
target's own table only, the catalogue entries that cover its parts and the open knob issues among #582 to #588 it
still needs.

Publication: one pull request. It starts after S1 is on `main` so the gallery reads the shipped catalogue.

### S3. Acceptance review and release check

`docs/archive/reviews/issue-718-target-parts-catalogue-acceptance-review-2026-10-02.md` with the literal-acceptance
marker, the issue body and comments re-fetched immediately before writing, one row per acceptance criterion and per
rule of the issue, successor links for the narrowed rows. Then the exact-main three-OS run on the review commit
(workflow dispatch), and a closing comment citing it only when ubuntu, macOS, Windows and the newest-Python
reproduction are green on that commit.

## Owned files and ordering

Documents first (plan, design, review, this plan: four small pull requests), then S1, S2, S3. A pull request is rebased
on the current derived-sync commit of `main` before its merge, and merged only while holding the merge lock.

## Risks and rollbacks

- *A part looks wrong at gate size.* Mitigation: scratch renders through the product are inspected before S1 merges; a
  fix changes the source and the regenerated catalogue in the same pull request.
- *The catalogue identity changes after S1.* A later change is a new id (`-v2026-11`), never an edit; the manifest hash
  test fails otherwise.
- *Wheel budget.* Expected growth is about 31 KB uncompressed; the check runs in S1.
- *Rollback.* Delete the four resource files, their test entries and the two list lines; nothing else references them.
