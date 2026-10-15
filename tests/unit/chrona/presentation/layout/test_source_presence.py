from chrona.presentation.layout.engine import solve_layout
from chrona.presentation.layout.model import ResolvedLayoutProfile
from chrona.presentation.layout.source_presence import (
    omit_absent_layout_sources,
    omit_absent_sources,
)


def _slot(node_id, source):
    return {
        "id": node_id,
        "kind": "slot",
        "source": source,
        "inlineSize": {"fixed": 40},
        "blockSize": {"fixed": 20},
        "place": {"inline": "start", "block": "start", "safety": "safe"},
        "priority": "required",
        "overflow": "visible-overflow",
        "frame": {"paint": "countdown"},
    }


def _container(node_id, kind, children, *, frame=None):
    result = {
        "id": node_id,
        "kind": kind,
        "inlineSize": "fill",
        "blockSize": "content",
        "children": children,
    }
    if kind in {"row", "column", "flow"}:
        result.update(gap=0, padding=0, alignItems="stretch", justifyContent="start")
    elif kind == "grid":
        result.update(columnTracks=["fill"], rowTracks=["content"], gap=0, padding=0,
                      alignItems="stretch", justifyContent="start")
    else:
        result["padding"] = 0
    if frame is not None:
        result["frame"] = {"paint": frame}
    return result


def test_empty_absence_set_returns_the_original_profile():
    profile = {"id": "test", "root": _container("root", "column", [_slot("summary", "summary")])}

    assert omit_absent_sources(profile, frozenset()) is profile


def test_absent_required_slot_prunes_framed_ancestor_chain_but_preserves_live_sibling():
    source_branch = _container(
        "bezel", "column",
        [_container("countdown", "overlay", [_slot("summary", "summary")], frame="countdown")],
        frame="bezel",
    )
    live = _slot("title", "title")
    profile = {"id": "test", "root": _container("root", "row", [source_branch, live])}

    result = omit_absent_sources(profile, frozenset({"summary"}))

    assert profile["root"]["children"] == [source_branch, live]
    assert result["root"]["children"] == [live]
    assert result["root"]["children"][0] is live
    assert result["root"]["id"] == "root"


def test_pruning_is_generic_across_child_container_kinds_and_preserves_empty_nodes():
    # The helper follows the tree's `children` relation instead of baking in a
    # list of container kinds. Authored empty/decorative nodes are not absence.
    empty = _container("empty", "overlay", [], frame="ornament")
    tree = empty
    for index, kind in enumerate(("layer", "stack", "flow", "grid", "overlay", "column", "row")):
        tree = _container(f"node-{index}", kind, [tree, _slot(f"s-{index}", "gone")], frame=f"f-{index}")
    profile = {"id": "test", "root": _container("root", "column", [tree, empty])}

    result = omit_absent_sources(profile, frozenset({"gone"}))

    # The populated chain exists only because its deepest authored empty node
    # was preserved; each mixed parent therefore also remains.
    retained_chain = result["root"]["children"][0]
    assert retained_chain["id"] == "node-6"
    assert retained_chain["frame"] == {"paint": "f-6"}
    assert result["root"]["children"][1] is empty

    def sources(node):
        if node["kind"] == "slot":
            return {node["source"]}
        return set().union(*(sources(child) for child in node.get("children", ())))

    assert sources(retained_chain) == set()


def test_all_absent_root_becomes_unframed_engine_only_empty_column():
    authored_root = _container("root", "overlay", [_slot("summary", "summary")], frame="page")
    profile = {
        "id": "test",
        "flowDirection": "horizontal",
        "dependencyNetworkFlowDirection": "horizontal",
        "reviewSurface": {
            "rowDistribution": "pack",
            "backgroundExtents": {},
            "annotationRouting": {"maxBends": 4, "maxDetourRatio": 2},
        },
        "root": authored_root,
    }

    resolved = ResolvedLayoutProfile("test", "authored-hash", profile, {}, ())
    result = omit_absent_layout_sources(resolved, frozenset({"summary"}))

    assert result.profile["root"] == {
        "id": "root",
        "kind": "column",
        "inlineSize": "fill",
        "blockSize": "content",
        "gap": 0,
        "padding": 0,
        "alignItems": "stretch",
        "justifyContent": "start",
        "children": [],
    }
    assert "frame" not in result.profile["root"]
    assert result.content_hash == "authored-hash"
    assert result.distances["/root/gap"] == 0
    assert result.distances["/root/padding"] == 0
    manifest = solve_layout(result, viewport_inline=100, viewport_block=100, measurements={})
    assert tuple(item.node_id for item in manifest.decisions) == ("root",)
    assert manifest.decisions[0].frame is None


def test_resolved_profile_distance_and_literal_paths_follow_surviving_node_ids():
    absent = _slot("omitted", "summary")
    nested_slot = _slot("kept-slot", "title")
    kept = _container("kept-container", "column", [nested_slot], frame="kept")
    profile = {"id": "test", "root": _container("root", "row", [absent, kept])}
    distances = {
        "/root/gap": 1,
        "/root/children/0/inlineSize/fixed": 99,
        "/root/children/1/padding": 2,
        "/root/children/1/gap": 3,
        "/root/children/1/children/0/inlineSize/fixed": 4,
        "/reviewSurface/maxBlockSize": 50,
    }
    literals = ("/root/children/0/inlineSize/fixed", "/root/children/1/gap",
                "/reviewSurface/maxBlockSize")
    original = ResolvedLayoutProfile("test", "authored-hash", profile, distances, literals)

    result = omit_absent_layout_sources(original, frozenset({"summary"}))

    assert result.profile["root"]["children"][0]["id"] == "kept-container"
    assert result.distances == {
        "/root/gap": 1,
        "/root/children/0/padding": 2,
        "/root/children/0/gap": 3,
        "/root/children/0/children/0/inlineSize/fixed": 4,
        "/reviewSurface/maxBlockSize": 50,
    }
    assert result.literal_distance_paths == ("/reviewSurface/maxBlockSize", "/root/children/0/gap")
    assert original.profile["root"]["children"][0] is absent
    assert original.distances["/root/children/0/inlineSize/fixed"] == 99
    assert result.content_hash == "authored-hash"
