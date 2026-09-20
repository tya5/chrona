# Presentation Settings Externalization: Implementation Plan

**Current state: design, schemas, and fixtures only. Implementation has not started.**

| Phase | Work | Exit condition |
|---|---|---|
| P1 | Resolve v0.2 settings, fixed bases, type checks, View/Style/Theme/Context connections, and migration adapter | Reject missing values, cycles, duplicate ownership, and unknown settings. Current YAML can be migrated. |
| P2 | Unify font metrics, locale, viewport, and region solver | No manual width coefficients. Validate Japanese/long text, min/max behavior, and unresolved assets. |
| P3 | Consume every Theme role, Detail string, and Layout dimension in Gantt | Every one of the 78 item groups is traceable from schema through resolved value to Scene consumption. |
| P4 | Consolidate legacy render, legacy review, summary, notes, and legend into the common path | Every public output consumes only settings for v0.2 input. Normalize v0.1 to an explicit legacy adapter with `E_PRESENTATION_LEGACY_ADAPTER`; do not complete v0.2 implicitly. |
| P5 | Test every setting mutation, multiple presets, real-image comparison, reproducibility, and performance | Zero unused settings, zero implicit fallbacks, and updated/published reference SVG/PNG output. |

After validation and review, publish every phase non-force through the GitHub
integration. A design gap pauses the affected implementation while the owning
specification, schema, and fixtures are updated first. M23 supplier tables and
additional dashboards are neither prerequisites nor completion conditions for this
plan.

## Test matrix

- Value range: zero, minimum, large, negative, wrong type, and unknown field.
- Connections: invariant View values, independent Actual, role resolution, font-asset
  change, and locale change.
- Placement: landscape- and portrait-like viewports, long task names, nested groups,
  and dense dependencies.
- Wording: Japanese legends, long labels, unknown placeholders, and malicious XML
  characters.
- Compatibility: migrate legacy surfaces, convert legacy renderer defaults into a
  preset, and reject duplicate declarations.
- Compatibility closure: do not infer font metrics or viewport from v0.1 alone.
  Require explicit v0.2 settings or emit the legacy-adapter diagnostic. Test complete
  v0.1-to-v0.2 migration separately with content-addressed metrics input.
- Validation: report schema validation, semantic diagnostics, and raster checks
  separately.
- Audit: inventory numeric, color, and wording literals in the AST. Keep the allowlist
  for mathematical constants, diagnostic IDs, and similar values narrowly justified,
  and detect new appearance literals in CI.
