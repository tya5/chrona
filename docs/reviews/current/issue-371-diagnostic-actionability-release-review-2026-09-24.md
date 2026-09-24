# Issue #371 — Diagnostic Actionability Release Review

**Decision:** Accept locally; GitHub Actions verification pending

## Requirement audit

| Requirement | Evidence | Result |
| --- | --- | --- |
| Dispositioned reachable diagnostics | `diagnosticActionability` has a validated default backlog plus only live code-specific entries; the generated inventory renders its actionability backlog before individual sites. | Pass |
| No stale policy exemptions | `tools/diagnostic_inventory.py --check` rejects a policy entry for a code with no bare CLI-reachable construction.  `E_CLOSURE_KIND`, `E_STORE_REFERENCE`, and `E_MATERIALIZER_CONTEXT` no longer require entries. | Pass |
| Public reachability | The inventory traces imports from `chrona.app.cli` and `chrona.__main__`; a focused fixture proves a transitively imported presentation module is `user-facing-ingress`. | Pass |
| Actionable closure diagnostics | Contract and closure sites include resource identity/reference plus expected and found kind or type.  Parser completion eliminates the last eight bare contract constructions. | Pass |
| Actionable store and materializer diagnostics | Local snapshot failures name the expected local identity/reference outcome; materializer context failures name manifest/slide/context/reference expectations. | Pass |
| Declared concurrency classification | The generated declared-value inventory classifies `baseRevision` as `pinned-deliberately`, produced by the Chrona workspace revision. | Pass |
| Architectural boundaries | The import-direction gate reports 9 packages and 33 edges, all inward.  Runtime diagnostic ownership stays at closure, store, or materializer; inventory tooling remains outside `src/chrona`. | Pass |
| Rendering preservation | Every declared public materializer slide reproduces its committed SVG byte-for-byte; no generated SVG changed. | Pass |

## Verification evidence

- Focused diagnostic inventory, contract, authoring, presentation closure, and
  draft closure tests: **31 passed**.
- `conformance/run_conformance.py`, module reachability, Scene primitive
  delivery, View dispatch reachability, import direction, text encoding,
  diagnostic inventory, declared-value inventory, documented-command, and
  init-template checks: **passed**.
- Public materializer reproduction: **22 passed**; generated SVG diff empty.
- Full parallel suite: **722 passed, 17 skipped**.
- Built wheel: `chrona-0.1.0a0-py3-none-any.whl`, **2,373,928 bytes**;
  forced installed-wheel smoke outside the checkout: **passed**.  The editable
  development installation was restored afterwards.

## Review conclusion

The release eliminates selected high-frequency bare diagnostics at their
semantic owners rather than making the CLI synthesize explanations.  Import
reachability corrects the tooling model without turning source layout into a
public-interface authority.  No presentation, Layout, Scene, scheduling, or
identity behavior changed; the materializer byte gate confirms that this
diagnostic and reporting work has no rendered-output side effect.

GitHub Actions on this exact release-review commit remains the final release
gate before closing Issue #371.
