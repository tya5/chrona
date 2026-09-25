# Acceptance Review: contract evidence and registry integrity (#392, #393, #401)

## Accepted result

| Issue | Accepted evidence |
| --- | --- |
| #392 | Generic schema traversal reaches `if`/`then`, unions, maps and nested finite values. The generated report lists all marker and symbol shapes, including unrealized shapes. Its bytes are LF and POSIX-path deterministic on Windows, macOS and Linux. |
| #393 | Annotation text emits `annotation-text`, not decoration purpose `annotation`. The CI AST gate verifies every declared semantic has a Layout/Scene production-carried lookup path; `iconMark` is reachable and remains a corpus-evidence gap. |
| #401 | Render Context v0.15, contract validation, draft CLI ingress and formatter behavior agree on exactly `en-US` and `ja-JP`. Historical schemas remain historical. |

## Architecture review

The implementation preserves the schema → normalized contract → Layout → Scene
→ adapter authority chain.  It adds no renderer policy, host locale fallback,
or corpus-driven input rejection.  The generated coverage report is evidence
only; the semantic reachability gate is structural delivery assurance.  This
matches the ownership and finite-capability boundaries in Specifications 32,
63 and 64.

## Verification

* Focused coverage/registry tests: 8 passed; contract, Scene, CLI, and public
  materializer focused tests: 88 passed; materializer integration: 24 passed.
* Conformance, documented-command execution, module/Scene/View/registry
  reachability, import-direction, text-encoding, and coverage freshness:
  passed.
* Public materializer regenerated only Controller Z annotation Scene/SVG;
  the visible change is the corrected `data-purpose="annotation-text"`.
* Three-platform CI, including full parallel test suite, wheel build and
  installed-wheel smoke: passed in
  [run 36086993577](https://github.com/tya5/chrona/actions/runs/36086993577).

## Disposition

Close #392, #393 and #401.  The still-unrealized mark icon and shapes are
intentional inputs to Program B's corpus evidence slice, not residual registry
or coverage defects.
