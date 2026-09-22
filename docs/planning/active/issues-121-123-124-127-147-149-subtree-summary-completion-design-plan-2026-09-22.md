# Subtree Summary Completion — Design Plan

## Objective

Complete the missing semantic rule for P4's `scope: subtree` typed summary
metric before implementation resumes.

## Design steps

1. Trace the existing object/planned metric from the summary schema through
   View projection and summary normalization, distinguishing its scalar value
   from Project rollup schedule and Layout geometry.
2. Define the aggregation, eligibility, empty-input behavior, and
   comparison-track treatment from selected View members only.
3. Review the decision against the Project → View → summary → Layout → Scene
   → renderer authority chain and record excluded general aggregation scope.
4. Publish the correction, architecture review, and a narrowly sequenced P4
   implementation amendment before changing executable contracts.

## Exit criteria

The correction gives one deterministic value for every legal scoped metric,
names rejection conditions, preserves existing unscoped metrics, and assigns
one owner to membership, scalar normalization, geometry, and serialization.
