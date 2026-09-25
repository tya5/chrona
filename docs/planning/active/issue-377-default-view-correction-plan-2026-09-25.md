# Design Correction Plan: Generic draft default View (#377)

**Status:** Active correction.

## Trigger

The proposed default reused HALCYON's mission View, which selects fixed object
IDs and an explicit 2027 window.  It cannot truthfully be the default for an
arbitrary user Project.

## Required decision

Define the default View's selection, temporal window, comparison requirement,
grouping, and visible table content as generic authored policy.  It must not
derive a hidden project-specific preset or silently require Actual input.
