# Implementation Plan — `init --example` integrity (#727)

Baseline: [issue #727](https://github.com/tya5/chrona/issues/727) on `main` `6c46123a` (2026-10-01). Found by #723.
Design: [design](../../design/issue-727-init-example-integrity-design-2026-10-01.md). This record holds the acceptance and the slice order; behaviour lives in the design.

## Published, inferred, unverified

Published (read on `main`): the #727 and #723 issues, the #723 design, plan and review, ADR-0030, `usecases/local_authoring.py`, `operational/store_config.py`, `app/cli.py` (`render-review`), README, `docs/guides/first-project.md`.
Measured: `render-review` does not read the Store config.
Unverified: Windows behaviour (the tests decide from data; the three-OS run on `main` is the check).

## Literal acceptance (issue #727)

- [ ] The documented path from `chrona init --example` to a rendered example Context works, with the chosen option stated in the guide and covered by a test that runs it.

## Slices

1. **I727-1 (docs).** This design and plan.
2. **I727-2 (code).** `init --example` writes `integrity: optional` with a comment; `render-review --store-config`; README and first-project guide make the path runnable and state option 3; Spec 42 and the #723 design/plan wording qualified; the end-to-end test and its mutation check.

Not changed: #723's reader and config defaults, ADR-0030, the example Contexts, derived docs.
