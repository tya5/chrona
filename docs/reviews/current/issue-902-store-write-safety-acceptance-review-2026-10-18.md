<!-- chrona:literal-acceptance/v1 -->

# Issue 902 — Store write safety (item 5)

## Literal issue acceptance

### Issue #902

- Source: [Issue #902](https://github.com/tya5/chrona/issues/902)
- Observed: 2026-10-18

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Acceptance for 2, 3 and 5: each has its own stale-base, replay and no-overwrite tests, plus an MCP stdio test where it is a tool. | met | Item5 focused evidence: [stale adapter/process](../../../tests/integration/test_actual_store_concurrency.py), [replay/no-overwrite](../../../tests/integration/test_store_write_lock.py), [transaction span](../../../tests/integration/test_store_transaction_span.py) and [MCP stdio](../../../tests/mcp/test_mcp_stdio_e2e.py). This does not accept items2/3. | — |
| 2 | Item 5 needs a two-process test that shows a lost update today and none after the fix. | met | [Two spawned adapters](../../../tests/integration/test_actual_store_concurrency.py): regression605232991 fails before9dcf22c16 and passes after; immutable post-A files are unchanged. [Persistent process exclusion](../../../tests/unit/chrona/storage/test_store_lock.py) remains mandatory native Windows evidence below. | — |

## Programme-level criteria (optional)

**Item5 release accepted.** [Exact-main39105269292](https://github.com/tya5/chrona/actions/runs/39105269292)
on `381cf404ac678446b68ede5f34125a1c1164c6d3` passed full pytest/conformance
and wheel/smoke on Linux, macOS and Windows, plus MCP and newest-Python public
materializer reproduction. The retained native persistent-exclusion,
same-command replay, transaction-span and snapshot-registry tests now pass.

Design correction `d0ea4f635`/Spec15 and [reviewed plan6246530666](https://github.com/tya5/chrona/issues/902#issuecomment-6246530666)
precede repair. The shared storage primitive now locks offset0 without content
I/O, valid even past EOF under [Microsoft's CRT contract](https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/locking?view=msvc-170).
Root and independent review confirm unchanged canonical-root/thread/reentrant
ownership, authoring diagnostic translation and replay→CAS→publish→record scope.
No sentinel migration, unlink, new retry, schema or renderer policy is added.

The guarded-handle regression fails3 empty/nonempty cases before the fix and
passes afterward; the focused storage/authoring/process batch passes58.
Repair PR1707 head `a0f42ce9a` passed final CI39104093015; its official artifact
12127409514 has all109 generated paths unchanged. The exact-main full release
above supplies native Windows proof beyond that portable regression. Parent902
remains open: this accepts item5 only, not item3, item2 or parked requirements.
