# R0 Issue Remediation Acceptance Review

**Disposition:** Accepted — GitHub issues 1–10 have current evidence and no accepted
defect remains open in the authorized remediation scope.

## Scope and authority

This review closes the program defined by
`../planning/issue-remediation-program-2026-09-20.md`. It reviews only the accepted
repairs to M0, M1, M5, and M22. It does not authorize or implement the deferred M23
review-detail surfaces.

All semantic decisions were published in D0 before implementation. When I2 discovered
that redistributable font outlines were unavailable, implementation stopped and the
owning design was corrected to require content-addressed metrics tables before I2
resumed.

## Phase evidence

| Phase | Published commit | Accepted evidence |
|---|---|---|
| D0 | `a1629f5` | Living-specification authority, manifest/link correction, unique ADR numbering, closed Core/CLI/font/presentation contracts, and issue traceability. |
| I0 | `70a558b` | Issues 1–3 and the calendar/anchor portion of issue 7; stable output across hash seeds; diagnostics replace exceptions or silent anchor movement. |
| I1 | `ddad395` | Issues 4, 5, and the CLI portion of issue 7; explicit raw/snapshot modes, common-Scene settings input, isolated legacy layout, and controller-x regression. |
| I2 design correction | `734d423` | Metrics-table assets replace an unavailable redistributable-font assumption before implementation continues. |
| I2 | `821edb3` | Issue 6; no host font discovery or font-file opening in the product path; content, family, and weight identity checks. |
| I3 | `e53e603` | Issues 8–10; declared axis formats/year, point and arrow shapes, facet opacity, and independent planned/Actual heights are consumed. |

## Issue disposition

| Issue | Final disposition | Evidence |
|---|---|---|
| #1 | Resolved | Project-order evaluation and return order; multi-hash-seed regression. |
| #2 | Resolved | Endpoint/mode semantic diagnostic, parsed composite WorkPeriod detection, and internal diagnostic fallback. |
| #3 | Resolved | Authoritative anchors are not moved; contradictory bounds diagnose; end bounds retreat correctly. |
| #4 | Resolved | The explicit legacy adapter has separate title, label gutter, rows, bars, and ticks; controller-x is a checked regression artifact. |
| #5 | Resolved | The repository declares a living versioned specification, the manifest paths are current, ADR numbers are unique, and v0.1 legacy extensions remain readable but are not treated as reproducibly executable. |
| #6 | Resolved | Rendering uses declared content-addressed font-metrics tables and no host-selected font file. |
| #7 | Resolved for every accepted sub-finding | Empty calendars and non-working anchors reject; CLI and documentation are current; conformance is executable. CLI reachability is not used to misclassify library/service modules as orphaned. |
| #8 | Resolved | All declared month and quarter formats plus the year level are consumed by the shared Scene formatter. |
| #9 | Resolved | Point size and diamond/circle/square shapes plus triangle/chevron/none arrow shapes are retained by Scene and serialized. |
| #10 | Resolved | Planned and Actual heights remain independently observable; facet opacity is consumed and covered separately. |

## Verification

The final verification was executed from the tree whose parent publication is
`e53e603`:

- `uv run --extra dev pytest`: **207 passed**;
- `uv run --extra dev python timeline-design/docs/fixtures/run_conformance.py`:
  **Chrona conformance PASS**, including temporal, Revision Store, Presentation,
  Federation, delivery-profile, traceability, release, DateTime, review-profile, and
  successor acceptance stages;
- ASTER's five SVG/PNG/HTML artifacts remain the accepted I3 output; their title,
  subtitle, axis labels, table content, marks, routes, legend, and coverage were
  visually reviewed before I3 publication;
- the only reported warnings are the pre-existing `jsonschema.RefResolver`
  deprecations and do not change acceptance.

## Conclusion

M22 returns to `Complete`. The issue-remediation program is no longer a provisional
area in the artifact manifest. After the commit containing this review is published and
its tree is verified, issues 1–10 may be closed with links to their phase evidence and
that exact R0 commit.
