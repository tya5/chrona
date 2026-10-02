# Implementation Plan — Store address leftovers from #710 (#731)

Baseline: [issue #731](https://github.com/tya5/chrona/issues/731) on `main` `6c46123a` (2026-10-01); first item of P1a on the owner's board.
Design: [design](../../design/issue-731-store-address-leftovers-design-2026-10-01.md). Predecessor record:
[#710 acceptance review](../reviews/issue-710-store-address-containment-acceptance-review-2026-10-01.md).
This record holds the baseline, the literal acceptance and the slice order; behaviour lives in the design.

## Published, inferred, unverified

Published (read on `main`): the issue body and the reviewer's added item, the #710 design, plan and acceptance review, Spec 56 §3.2 and §7,
`schemas/common-v0.1.schema.yaml` (`storeAddress`, `fileName`), `src/chrona/core/store_address.py` and every caller of it,
`tests/unit/chrona/test_store_address_containment.py`, `tests/unit/tools/test_store_address_{schema,retirement}.py`, the schema inventory, the
three leftover sites and their consumers (`extensions/profiles.py`, `presentation/model/closure.py`, `usecases/preset_library.py`).

Measured with throwaway scripts (not committed): the guard against the schema on 30,941 strings, the per-site verdict table, the version-string
counts per predecessor.

Inferred: nothing relied on without a measurement; the three-OS behaviour is decided from data and path flavours, not run on Windows here.

Unverified: whether a Windows path segment of three or more dots can alias a parent (the guard is conservative, as in #710).

## Literal acceptance (issue #731 body and comment)

| # | Row | Slice | Status |
| --- | --- | --- | --- |
| 1a | Project `extensions[].resource` (loose `revision-store-resource-ref-v0.1` via `extensions/profiles.py`): decide whether it moves | B, D | decided: unchanged (never opened; tightening needs a Project bump); owner question open (design B3, B5.3) |
| 1b | `icon-catalog-v0.4` `source.address` and `preset-library-v0.2` `address` end in `$`: reference `storeAddress` (bump) or stay | B, D | decided: consumers made strict, then in-place schema reference (design B5.1, B5.2); I731-D |
| 2 | Retire the five loose predecessors (`layout-profile` v0.9, `render-context` v0.16, `command-request` v0.2, `automation-result` v0.1, the authoring side of `snapshot-ref` v0.2); `snapshot-ref` v0.2 stays readable; decide when | C1 to C5 | pending |
| 3 | Record whether future address tightenings should use the in-place clause | B (Spec 56 §3.2 sentence) | in this slice |
| 4 | (reviewer) Align the runtime guard in `core/store_address.py` with the schema's `storeAddress` character rule | A | merged ([#754](https://github.com/tya5/chrona/pull/754), `aeed86fb`) |

## Slices

Each slice is its own PR, branched from a derived-ready `main`, `Refs #731` only, title ending in the slice id. None edits a derived document
(CI's derived-sync regenerates `docs/diagnostics/inventory.md`, `declared-value-inventory.md`, `vocabulary-inventory.md`,
`gallery/presentation-coverage.md` and `examples/*/generated/*` after merge, if anything changes).

### I731-0 — this record (documents only)

The design and this plan. Gate: conformance.

### I731-A — align the runtime guard with `storeAddress` (security relevant; first)

* `core/store_address.py`: `charset` keyword (`"address"` default, `"file-name"`) on `check_store_address`, `check_store_segment` and
  `resolve_store_address`; the address charset is a full match of `[A-Za-z0-9._-]+` per segment and no all-dot segment (design A2).
* Callers: the two identifier or file-name joins pass `charset="file-name"` (`commands/actual_commands.py`, `operational/command_engine.py`, and the
  workspace-name check in `operational/authoring_commands.py`, split from the resource-name check); every other caller keeps the default.
* Tests (data and path flavours only): exhaustive parity of the guard with the `storeAddress` validator; named vectors; both modes through
  `cas_write_authoring_aggregate` (`my plan.yaml`, `計画.yaml`) and `LocalActualStore` (id `作業 1`); the old accept lists that contain a space are updated.
* Gate: focused tests, `tests/unit`, conformance, `tools/check_import_direction.py`. Mutation check of every new rule in the PR body.
* Stop condition: a committed or packaged address, or a working file-name caller, newly refused.

### I731-B — the in-place reading in the specification; the three sites

* No schema, pattern or expected-delta change: the per-site verification (design B1 to B3) shows that no site meets the premise. Spec 56 §3.2
  gets one sentence recording the reading and its condition. Gate: conformance, `python -m tools.schema_equivalence --base-rev origin/main`
  (must report no delta).
* The three sites stay open for the lead's decision (options in design B4).

### I731-D — make the consumers strict, then move the two schema sites in place

Design B5. Branch from a derived-ready `main`.

* Docs PR (this addendum), then one code PR (two if clearer).
* Consumers: `preset_library._safe` uses `check_store_address`; `_icon_catalog_contract` checks every v0.4 raster `source.address` at parse time
  (`E_ICON_ASSET_PATH`). Tests decide from data (the `storeAddress` validator, narrowed vectors, no host OS); each new check gets a mutation check.
* Schemas: `preset-library-v0.2` `address` and `icon-catalog-v0.4` `rasterSource.address` reference `storeAddress` in place. S0 gate against
  `origin/main` lists every moved verdict (L1 pointers; L3 probes; the leading `.`, `_`, `-` widening) with a test each.
* Gate: focused tests, `tests/unit`, schema tools, conformance, import direction, `derived_evidence --check`,
  `regenerate_public_examples --check`, wheel build plus `tools/wheel_smoke.py`. A source edit shifts diagnostic line numbers; CI's derived-sync
  regenerates `docs/diagnostics/inventory.md`.
* Stop conditions: a committed, packaged or test address newly refused; a load-time regression of the catalog parse.

### I731-C1 … C5 — retire the predecessors, one PR each

Order: C1 `layout-profile` v0.9, C2 `render-context` v0.16, C3 `command-request` v0.2, C4 `automation-result` v0.1, C5 the authoring side of
`snapshot-ref` v0.2. Each: scripted migration of every remaining document and test to the successor (dry run, counted replacements, diff
summary); delete the registration and parser path; `git mv` the schema to `docs/archive/schemas/`; remove the `transitioning` inventory entry;
update `tests/unit/tools/test_store_address_retirement.py` and the Spec 56 retirement paragraph. Gate: focused tests, `tests/unit`, the schema
tools, conformance, import direction, the S0 gate against `origin/main` (the removal is listed, not hidden), `python -m tools.derived_evidence
--check`, `python -m tools.regenerate_public_examples --check`, and a wheel build plus `tools/wheel_smoke.py` (a shipped schema moves). A
slice that is too large is split and says so.
Stop conditions: a Scene byte changes, or a committed or packaged document is newly rejected.

## Publication boundary

Separate PRs, merged in the order above, each after `derived-ready` and `pr-title` pass. #731 is not closed here and #454 is not touched; the
acceptance review is written by the lead after the last slice.
