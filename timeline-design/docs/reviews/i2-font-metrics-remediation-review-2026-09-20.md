# I2 Font Metrics Remediation Review

**Conclusion:** Accepted. Presentation measurement no longer discovers or opens a host
font at runtime.

## Evidence

- Regular and bold Nimbus Sans metrics are checked-in
  `chrona/font-metrics/v1` tables with exact content identities.
- The resolver confines relative paths to an explicit asset root and verifies table
  bytes, version, family, weight, and numeric metrics.
- Identity mismatch, weight mismatch, traversal, malformed data, and unavailable
  tables normalize to `E_FONT_METRICS_UNAVAILABLE`.
- Product and test code contain no `fc-match` or `TTFont` runtime call. The explicit
  generator remains a build-time tool whose input font path is supplied by its caller.
- Presentation resources and the built-in base name exact table paths and identities.
- CI runs the full conformance and test commands on both Ubuntu and macOS.

The metrics were generated from the same regular/bold font files used by the previous
Linux evidence, so existing Scene geometry and accepted SVG bytes remain unchanged.
