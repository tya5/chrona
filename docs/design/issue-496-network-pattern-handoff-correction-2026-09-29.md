# #496 network-node pattern handoff correction

**Status:** Accepted before Slice 2 network code. **Authority:** Specifications 07, 08, and 64.

`network-node.pattern` is an admitted always-Rect role, but network composition uses `compose_dependency_network_layout`, not the table surface composer. Pass the already-resolved Theme pattern catalogue map into that Layout function; it completes one pattern placement per network node from the node's completed Rect bounds and corner geometry. `DependencyNetworkLayout` returns those typed placements keyed by exact node placement ID. Scene projects them without choosing region, phase, clip, or asset. No new role, version, or adapter behavior is introduced.
