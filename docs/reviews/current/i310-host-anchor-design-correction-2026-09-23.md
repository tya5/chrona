# I310 Design Correction: Inside Labels Follow Their Actual Host Mark

## Trigger

An explicit View row may select `source.kind: actual`.  The pre-correction
Layout code nevertheless anchored every member label to `planned:<instance>`,
while Scene selected the `memberLabelInsideActual` role from the source kind.
The role whose contrast was validated could therefore differ from the mark
that physically hosted the label.

## Corrected design

Layout selects a label's host mark before it evaluates the side ladder:

| Selected source kind | host placement | host semantic |
| --- | --- | --- |
| `primary`, `combined` | `planned:<instance>` | planned |
| `actual` | `actual:<instance>` | actual |
| `snapshot` | `planned:<instance>` | snapshot |
| `scenario` | `planned:<instance>` | scenario |

The selected host placement supplies both the anchor and the identity-safe
inside-obstacle exemption.  An explicit actual source whose actual placement
is unavailable is a Layout error; it does not silently fall back to planned.
Snapshot and scenario retain their existing planned placement geometry while
their distinct semantic fills determine contrast.

Scene uses the same closed source-kind-to-host-semantic mapping when it turns a
selected `inside` rung into one of the four inside-label semantics.  This makes
the completed Layout host, the Scene visual role, and Theme/Scheme pairwise
contrast refer to the same visual mark.

## Architecture review

View still names a source and placement preference; Layout owns mark selection,
geometry and collision identity; Scene owns semantic projection; Theme/Scheme
owns colour validation; renderers serialize completed primitives.  No layer
infers an alternative host from renderer geometry or literal colour.

## Implementation amendment

Centralize the closed host-semantic mapping, select the corresponding completed
mark in Layout, and add explicit-row actual coverage that proves both the
actual anchor and actual inside-label role.  Update the output property gate
to accept contrast-safe overlap only with the matching planned or actual host
identity, never with an unrelated mark.
