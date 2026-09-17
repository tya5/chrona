# Core v0.1 Semantic Rules

**Status:** Proposed companion specification

This document condenses the most important Core rules into a reviewable table.

| Rule | Normative meaning |
|---|---|
| Span interval | `[start, end)` |
| Empty span | invalid; use Point |
| Date vs DateTime | no implicit conversion |
| `0wd` | identity |
| Calendar `1w` | seven calendar days |
| `1mo` | calendar month field arithmetic with clamp |
| Scheduled Date span | positive `d`, `w`, or `wd` amount |
| `mo`/`y` task duration | invalid in Core v0.1 |
| Dependency | `target.endpoint >= advance(source.endpoint, lag)` |
| FS | `end -> start` |
| SS | `start -> start` |
| FF | `end -> end` |
| SF | `start -> end` |
| Fixed target dependency | validation bound; target does not move |
| Scheduled target dependency | placement lower bound |
| Deadline | indicator/target; not a bound |
| WorkPeriod lag calendar | explicit relation -> target -> project |
| Relation calendar adjustment | none; relation computes bound |
| Target calendar adjustment | scheduler finds valid placement after bound |
| Cycle | not automatically invalid |
| Positive contradictory cycle | unsatisfiable |
| View/Style/Theme | cannot affect schedule |

| Explicit scheduled anchor | authoritative; conflicting bound is an error |
| Candidate WorkPeriod start | normalize forward to first valid working date |
| `1wd` scheduled span | one working-date interval; end is next working boundary |
| Core v0.1 scheduler profile | Date-based; DateTime scheduling optional |
| Diagnostic IDs | normative; messages are not |
