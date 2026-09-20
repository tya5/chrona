# Presentation Theme Expression Design

**Status:** Design complete  
**Owns:** M17 role coverage and accessible light/dark expression.

M17 extends the existing Style/Theme contract without adding selectors. Standard roles
now include `table-header`, `table-cell`, `axis-major`, `axis-minor`, `group-header`,
`group-separator`, `group-band`, `summary-panel`, `summary-unknown`, and
`routed-connector` in addition to M14 comparison roles. A required role without a
resolved token is an error, never an adapter default.

The light executive and dark delivery-control themes bind this identical role catalog.
They must distinguish planned/Actual, normal/exception, semantic/explanatory relation,
and available/unknown summary states through non-colour cues as well as colour. Theme
does not select columns, determine panel geometry, or alter calculated values.

The acceptance gallery consists of declared semantic samples and deterministic SVG
assertions: role completeness, text alternatives, source metadata, contrast policy,
and equal output on repeated input. Pixel similarity alone is not acceptance evidence.
Theme IDs are data: an adapter MUST resolve declared roles/tokens generically and MUST
NOT contain light-executive or delivery-control conditionals.
