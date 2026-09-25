# Implementation Plan — Portable Scene Report Encoding (#446)

1. Configure the tool's writable stdout stream as UTF-8 before reporting.
2. Add a focused seam proving Unicode report text reaches the output writer
   unchanged.
3. Run focused tool/conformance checks, then use one three-platform CI release
   result.  Do not alter Scene findings or add an OS-specific fallback.
