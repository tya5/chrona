# Architecture Review — Shared-Track Order and Summary-Bar Geometry (#417)

**Result:** Accepted.

The source-kind sequence is neither a Theme choice nor a Layout allocation:
it expresses the stable semantic order of normalized comparison members.  A
model-level finite policy therefore prevents both Layout/Scene drift and the
incorrect coupling of reading order to paint order.  The Theme-owned
summary-bar height removes an otherwise unreviewable geometric literal while
leaving row allocation in Layout.  This preserves the Project → View → model →
Theme → Layout → Scene → adapter ownership chain.
