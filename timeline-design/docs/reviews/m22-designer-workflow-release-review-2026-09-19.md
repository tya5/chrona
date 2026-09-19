# M22 Designer Workflow Release Review — 2026-09-19

**Disposition:** Pass — M22 complete.

`validate_designer_preset` is the common declarative gateway for human-authored and
AI-proposed View/Style/Theme/Layout closures. It requires the complete named resource
set, rejects executable/SVG payload keys, reuses M19 Layout validation, and emits stable
resource hashes plus the Layout Manifest. It introduces no Project mutation or alternate
renderer path.

Release evidence: common-closure and executable-content tests, M19–M21 deterministic
artifacts, full conformance, and 92 passing tests. SVG remains the declared output target.
