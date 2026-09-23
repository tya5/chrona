# #349 Visual Profile Fidelity Release Review

**Decision:** accepted; #350 is unblocked.

The corrected contract has exact target profiles: SVG and PNG independently
admit v0.6, while PDF/Typst/TikZ remain baseline-only. A rich profile cannot
reach PDF, so its unavailable shadow cannot be silently dropped. Baseline
optional omission remains Scene policy; required unsupported treatment rejects
before an adapter is invoked.

Scene now completes canonical Layout-plane gradient endpoints from the declared
angle and bounds. SVG serializes those endpoints rather than interpreting an
angle in a target coordinate system. The Theme contract has only its authorable
two-stop vocabulary and treatment-specific fidelity bindings. Profile errors
retain a diagnostic message and precise Context/role pointer through CLI.

## Evidence

- Focused materializer/output/CLI/target checks: `93 passed, 9 skipped`.
- Full parallel pytest: `486 passed, 9 skipped`.
- Conformance and traceability: pass.
- Controller Z Elevated was regenerated through the public materializer.

The correction does not introduce an asset or icon input. #350 can therefore
define an icon catalog against a target capability mechanism which no longer
claims PDF fidelity it cannot provide.
