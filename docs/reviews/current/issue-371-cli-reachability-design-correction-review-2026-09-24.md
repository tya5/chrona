# Issue #371 — CLI Reachability Design Correction Review

**Decision:** Accepted correction before I371-1 implementation

The first import-graph implementation established that the #370 prefix list
was a subset, not a definition, of public diagnostic reachability. Restricting
the new policy to its 53 prior entries would again hide `E_ACTUAL_REQUIRED` and
equivalent public-path candidates. The corrected design classifies every bare
construction in a module reachable from public CLI roots; tools and tests stay
excluded. This expands quality evidence only and creates no runtime policy
import, presentation behavior, or compatibility path.
