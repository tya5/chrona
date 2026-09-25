# Design Correction — Minimal Template Package Topology (#376)

**Status:** Proposed for architecture review.

## Discovery and correction

Wheel assembly proved that `src/chrona/resources/templates/minimal/` is already
included by Hatch as package data beneath the declared `src/chrona` package.
Adding it to the wheel `force-include` table attempts to add identical archive
members twice and rejects the build.

The minimal template remains a wheel-owned package resource resolved through
`importlib.resources`.  The correction is solely its build declaration:
package-tree inclusion is the authoritative mechanism, and no `force-include`
entry is permitted for this subtree.  The external `examples/halcyon-1`
authority still requires its existing force-include because it lives outside
the package tree.

## Evidence

The release gate builds a wheel and reads the three minimal-template members
from an installed wheel outside the checkout.  This tests the intended runtime
contract directly and prevents a source-tree-only resource from returning.
