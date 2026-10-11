<!-- chrona:literal-acceptance/v1 -->

# Acceptance review — installed-font discovery no longer floods stderr (#1369)

Implementation: [#1371](https://github.com/tya5/chrona/pull/1371) (closed unmerged; commit `af70145f4` and merge `00931c744` landed through integration PR [#1389](https://github.com/tya5/chrona/pull/1389), merge `12f8c6eba`), checked against `origin/main` `12f8c6eba`. `InstalledFontIndex` now scans inside `_quiet_fonttools()`, which sets the `fontTools` logger to `ERROR` for the scan and restores the previous level in a `finally`. Plan: [Status comment](https://github.com/tya5/chrona/issues/1369).

## Literal issue acceptance

### Issue #1369

- Source: [Issue #1369](https://github.com/tya5/chrona/issues/1369) (body, assignment and Status comments)
- Observed: 2026-10-11

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | In a test, discovery over a directory containing a face with an old `created` timestamp writes nothing to stderr. | met | [`test_discovery_over_a_face_with_an_old_created_timestamp_writes_nothing_to_stderr`](../../../tests/unit/chrona/presentation/fonts/test_installed.py): a packaged face is saved with `head.created = 0` (1904), a stderr `StreamHandler` is attached to the `fontTools` logger at `NOTSET`, `InstalledFontIndex([tmp_path]).faces()` runs, and `capfd` must see empty stderr and stdout; the logger level is asserted restored. I checked that the test is a real guard: with the `setLevel(ERROR)` line replaced by `pass` in a scratch edit (reverted), the test fails (the captured log shows `'created' timestamp seems very low; regarding as unix timestamp`). Limit: it is the library scan, not an end-to-end `chrona render` on a host with real system fonts; macOS host behaviour was not re-measured. | — |
| 2 | Do not edit `examples/**`. Refs #1281. | met | No `examples/**` file in [#1371](https://github.com/tya5/chrona/pull/1371/files) (one source file, one test); no bot-generated file. | — |

## Programme-level criteria (optional)

The scope sentence offers "if a face genuinely can't be read, record it in an info diagnostic instead" as an option; it was not added (unreadable faces are skipped as before), and the acceptance rows do not require it. Warnings about a genuinely broken font are also silenced during the scan (level `ERROR` hides `WARNING`), which is the intended trade-off of the issue's first option. Both rows are met, so #1369 can close once this review is on `main` and the three-OS run on the commit that publishes it is cited (AGENTS.md); no full-matrix run exists yet for `12f8c6eba` (derived sync [38101760005](https://github.com/tya5/chrona/actions/runs/38101760005) was in progress when observed). The PDF limit of #1281 is [#1338](https://github.com/tya5/chrona/issues/1338), separate.
