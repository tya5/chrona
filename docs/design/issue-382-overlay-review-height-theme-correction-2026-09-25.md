# Design Correction: Overlay review-height token (#382)

**Decision:** Accepted.

## Corrected composition contract

The wallboard Theme gains `panel.review.block` as a numeric reusable design
token.  The overlay Layout Profile declares it in `requiredThemeTokens` and
uses it as the fixed block size of the main review container.  The guide
positions that container below the title; table and timeline inherit the
container's resolved block extent.  The declared 2560×1440 viewport leaves the
fixed region inside the padded overlay after the guide offset.

The token is owned by Theme because it is an appearance/composition metric that
can be deliberately reused by a future wallboard Layout; the Layout resource
only names it.  Existing layouts do not reference it and therefore have no
geometry change.

## Rejected alternatives

* raw `fixed: 900` in the Layout: reintroduces forbidden numeric layout
  authoring and cannot be semantically reused;
* `content` sizing: has empirically insufficient preferred height for the
  required 26-row timeline;
* `safe` overflow or a smaller View selection: hides required-content failure
  instead of declaring a feasible composition.

## Architecture alignment

The correction preserves Theme → Layout metric direction.  View still owns
programme selection; Layout owns the guide and block allocation; Scene and the
materializer retain no new constraint policy.  The exact required-token list
continues to make the cross-resource dependency reviewable.

## Acceptance

* The token is typed as a number and is exactly declared by the new Layout.
* The public materializer succeeds with the full programme-board selection.
* Existing materialized slides retain byte identity.
