# Design Correction — Corpus Evidence Cannot Use a Package-Provider View/Theme/Layout Reference

**Corrects:** [design](issue-429-383-preset-catalogue-design-2026-09-27.md) §5 ("Committed corpus evidence without a new mechanism"). **Found during:** I383-1 implementation, first attempt to materialize `examples/halcyon-1/contexts/13-gallery-editorial.yaml`.

## What the design claimed

§5 read `materialize.py`'s `_copy_reference`/`_reference_payload` as proof that a Render Context's `view`/`theme`/`colorScheme`/`layout` fields could use `{store: {provider: package, identity: chrona.resources}, address: presets/bundles/editorial/view.yaml, contentIdentity: ...}` today, with no code change, because that function already branches on `store.provider == "package"` generically for any reference kind.

## What actually happens

`_copy_reference` is only half the path. `materialize()` first calls `copy_context_closure` (which does copy package-provider bytes correctly, once the content identities were entered correctly — a real typo on the implementer's part cost two iterations, unrelated to this correction) and then calls `resolve_render_context(reference, LocalSnapshotReader(snapshot, reference["store"]["identity"]), ...)` on the **original, unmodified context document**. That second call is the actual render/closure path, and it goes through `_load_reference_source` → `LocalSnapshotReader.read()` (`src/chrona/storage/revision_store.py:197`), which requires `reference["store"]["provider"]` to be the reader's own local provider and raises `E_STORE_REFERENCE` otherwise ("expected local store identity=...; received store=..."). It has no package-provider branch at all. Confirmed by reproducing `E_STORE_REFERENCE` directly, then reading `revision_store.py:197`.

So `_copy_reference`'s package-provider branch exists only to let materialize **copy bytes into a snapshot**, not to let the **closure resolver read them back** as a package reference — the copied bytes are placed at the reference's own `address` inside the snapshot directory, but the reference itself is never rewritten to `provider: local`, so the second stage still tries to resolve the original `package` locator against a reader that only understands `local`. Font/font-metric locators avoid this because `copy_context_closure` explicitly rewrites `record["locator"] = {"provider": "context", "address": address}` for those specifically (`materialize.py:206`) before the closure stage runs; no equivalent rewrite exists for `view`/`theme`/`colorScheme`/`layout`/`detailProfile` references.

## Disposition

This phase does not extend `resolve_render_context`/`LocalSnapshotReader` to add that rewrite or a package-provider branch — that is a real, separable piece of work (touching the closure resolver's reference-loading contract, not just the preset catalogue) and is out of scope for #383/#429's literal acceptance, which asks only that the preset's corpus example "renders reproducibly" with "its SVG committed," not that it use any particular reference mechanism.

**Taken instead: the design's own named fallback (§5, "cheaper to fall back to if discovered early").** Editorial's View/Theme/Layout/Color Scheme/Review Detail Profile are copied byte-for-byte into `examples/halcyon-1/{views,themes,layouts,schemes,profiles}/` alongside the packaged bundle under `src/chrona/resources/presets/bundles/editorial/`, and `contexts/13-gallery-editorial.yaml` references the corpus copies with ordinary `provider: local` locators, exactly like every other HALCYON-1 slide. Byte-identity between the two locations is asserted directly (`cmp` verified for all five files) and covered by a new test (`tests/integration/test_public_examples.py`) that fails if either copy drifts from the other, so the duplication cannot silently rot.

## What a future fix would look like

If a later issue wants Contexts to reference wheel-packaged presentation resources directly (avoiding this duplication for the other three directions too), it needs: (a) `copy_context_closure` to rewrite `view`/`theme`/`colorScheme`/`layout`/`detailProfile` package-provider locators to `provider: context` after copying, exactly as it already does for font locators, and (b) confirmation that `resolve_render_context`'s later re-read of the *materialized* context (not the source one) picks up that rewrite. Named here rather than attempted now, since #429/#383 do not require it and it is unrelated to any of the four directions' visual content.
