# Issue #49 presentation regression recovery design plan

## Objective

Recover the 13 externally observed test failures and stale Controller Z evidence without reintroducing deleted legacy contracts.

## Design phases

1. Inventory each failed test and its authoritative boundary: View/Profile, Project/Actual, Theme, Layout measurement, Scene composition/routing, SVG/CLI, or materializer evidence.
2. Separate fixture drift from implementation regression; do not weaken an assertion merely to make a test pass.
3. Specify table-column measurement, group/header semantics, temporal marker/shading/axis/legend behavior, row/annotation routing, immutable closure behavior, and generated-evidence ownership.
4. Publish a cross-boundary review that verifies one-way flow from resources to Scene to SVG and checks compatibility.
5. Publish implementation plan only after every failure has a declared owner and acceptance test.

## Execution constraints

- Generated SVGs are created only by the public materializer.
- Full pytest is delegated through an external verification issue after focused changes.
- Each implementation phase is published through GitHub.