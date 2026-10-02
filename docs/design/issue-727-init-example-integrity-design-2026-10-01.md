# Design — The `init --example` Store and its own unpinned Contexts (#727)

**Plan:** [implementation plan](../archive/planning/issue-727-init-example-integrity-implementation-plan-2026-10-01.md).
**Found by:** #723 ([design](issue-723-content-identity-required-by-default-design-2026-10-01.md), risk 1).
Baseline: `main` at `6c46123a` (2026-10-01).

## Decision (lead, fixed): option 3

`chrona init --example <id>` writes `integrity: optional` into `.chrona/store.yaml` **explicitly**, with a YAML comment giving the reason. Every other Store keeps `required`: the plain `chrona init` (minimal starter), an omitted `integrity`, `LocalSnapshotReader`, `LocalBaselineRegistry`. #723's reader and config defaults are not touched. The example references are not pinned. ADR-0030 stays.

Why not the other options:

- **Option 1, pin the example references.** The canonical Contexts leave their inner references unpinned by design (ADR-0030, Spec 54; 191 unpinned against 17 pinned). Pinning reverses an accepted ADR and rewrites every canonical Context and the evidence derived from them, to protect a corpus that is not a trust boundary: the owner is the only user, the bytes ship in the package and are copied verbatim. All cost, no risk removed.
- **Option 2, keep `required` and tell the reader to pass `--allow-missing-content-identity`.** It makes the first-run path of the shipped example depend on an opt-out flag the reader must learn before the first success, and it teaches the opt-out as normal. The flag stays the explicit per-call escape for an author's own Store; it should not be the way the product's own example is read.

Option 3 states the exception where it applies: the example corpus only, visible in the file a person opens, with the reason beside it.

## Finding that widens the slice: `render-review` never reads the Store config

Measured on `main`: `chrona render-review` builds `LocalSnapshotReader(--snapshot-root, --store-identity, require_content_identity=not --allow-missing-content-identity)`. It does not discover or read `.chrona/store.yaml` (only `command-*`, `actual-*`, `baseline-*` use `--store-config`). So writing `integrity: optional` into the config alone changes nothing for the documented path: a person who runs `init --example` and then `render-review` still gets `E_CONTENT_IDENTITY_REQUIRED` unless they pass the flag. The decision's purpose, that the init'd Store config governs reading its own Contexts, needs `render-review` to be able to take that config.

Chosen minimal addition: `render-review --store-config PATH` (explicit only; no upward discovery here). With it, the reader root, identity and integrity come from the config entry whose `store` matches the Context reference; `--snapshot-root` and `--store-identity` become optional and are required only when `--store-config` is absent (checked in code, same rejection family). `--allow-missing-content-identity` still overrides to optional. Without `--store-config` the command is byte-for-byte what it is today. No default changes.

## The documented path had a second gap

README and `docs/guides/first-project.md` never say how to build `--context-reference`. The README `render-review` block is `doc-check skip` ("author-created reference"). The reference is a resource reference to a Context inside the init'd Store: `id`, `kind: render-context`, `store` and `revision` copied from the Context's `body.project`, and `address: contexts/<file>.yaml`. The guide gains a runnable block that writes this file from a shell heredoc and renders it with `--store-config .chrona/store.yaml`, and states that the example Store is `integrity: optional` and why.

## Minimal init

`chrona init` (no `--example`) writes no Store config at all, so it has no `integrity` line to write: any Store a person adds afterwards that omits `integrity` means `required` (#723). The test pins "no config written" and "omitted means required", not a `required` line that does not exist.

## Risks

1. **Option 3 contradicts the wording #723 published.** Spec 42 ("`chrona init --example` writes `integrity: required`"), the #723 design (what flips, item 3, and risk 1) and the #723 plan say `required`. Updated in the code PR; the #723 acceptance review is a dated record and is not edited (the lead rewrites acceptance).
2. **A copied example Store config stays `optional`.** Intended and commented in the file; an author's own Store is not created by `init --example`.
3. **Windows.** The tests decide from data (config contents, exit codes, error codes in the Context closure), not from the host OS; the `root` in the config is written absolute by `init` and read back. The three-OS run on `main` follows merge.
4. **Concurrent work** (#731 schemas and `store_address.py`, #709, #687) is not touched: edits are `local_authoring.py`, `app/cli.py` (the `render-review` parser and runner), docs.

## Verification

End to end in a temp directory: `init --example halcyon-1`; write the reference as the guide says; `render-review --store-config` succeeds with no allow flag; assert the config says `optional` with its comment; `chrona init` writes no config and an omitted-`integrity` config refuses an unpinned reference; an `integrity: required` copy of the same config refuses the same reference with `E_CONTENT_IDENTITY_REQUIRED`. Mutation: make init write `required` for the example; the e2e test fails.
