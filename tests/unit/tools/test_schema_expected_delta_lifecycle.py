"""#970: an L1 expected-delta entry is retired by Git history, not by hand.

Everything runs on a synthetic Git repository whose history is built here: a schema, the PR that changes it
together with its entry, and later merges that touch `schemas/` or something else.
"""
from copy import deepcopy
import dataclasses
from pathlib import Path
import subprocess

import pytest
import yaml

from tools import schema_equivalence as gate

THING = "thing-v0.1.schema.yaml"
OTHER = "other-v0.1.schema.yaml"
DELTAS = gate.EXPECTED_DELTAS.as_posix()
HEADER = f"# a comment line the prune must keep\nversion: {gate.EXPECTED_DELTAS_VERSION}\ndeltas:\n"
B = {"type": "string"}


def _entry(pointer: str, after, *, schema: str = THING, before=gate._MISSING, **extra) -> dict:
    entry = {"schema": schema, "pointer": pointer, "after": after, "reason": "r", "test": "t", **extra}
    if before is not gate._MISSING:
        entry["before"] = before
    return entry


def _line(entry: dict) -> str:
    return "  - " + yaml.safe_dump(entry, default_flow_style=True, width=10_000).strip() + "\n"


def _document(name: str, **properties) -> dict:
    return {"$id": f"urn:chrona:test:{name}", "type": "object", "properties": {"a": B, **properties}}


def _schema(name: str = THING, **properties) -> str:
    return yaml.safe_dump(_document(name, **properties))


class Repo:
    def __init__(self, root: Path):
        self.root = root
        self.git("init", "-q", "-b", "main")

    def git(self, *args: str) -> str:
        env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.org", "GIT_COMMITTER_NAME": "t",
               "GIT_COMMITTER_EMAIL": "t@example.org", "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"}
        return subprocess.run(("git", "-C", str(self.root), *args), check=True, capture_output=True, text=True,
                              env=env).stdout.strip()

    def commit(self, message: str, files: dict[str, str]) -> str:
        for name, text in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD")


def _deltas(*lines: str) -> str:
    return HEADER + "".join(lines)


@pytest.fixture
def history(tmp_path):
    """c0 base; c1 a PR adding property b with its entry; c2 and c3 later schema merges; c4 a docs merge."""
    repo = Repo(tmp_path)
    c0 = repo.commit("base", {f"schemas/{THING}": _schema(), f"schemas/{OTHER}": _schema(OTHER), DELTAS: _deltas()})
    entry = _entry("/properties/b", B)
    c1 = repo.commit("PR one (#1)", {f"schemas/{THING}": _schema(b=B), DELTAS: _deltas(_line(entry))})
    c2 = repo.commit("a later schema merge", {f"schemas/{OTHER}": _schema(OTHER, x=B)})
    c3 = repo.commit("another schema merge", {f"schemas/{OTHER}": _schema(OTHER, x=B, y=B)})
    c4 = repo.commit("docs only", {"README.md": "x\n"})
    return repo, (c0, c1, c2, c3, c4), entry


def _key(entry: dict) -> str:
    return gate.delta_key(gate.parse_deltas(("version: %s\ndeltas:\n" % gate.EXPECTED_DELTAS_VERSION).encode()
                                            + _line(entry).encode(), label="t")[0])


# --- landing commit and age ---------------------------------------------------------------------------

def test_an_entry_lands_in_the_commit_that_added_it_and_ages_by_schema_merges_only(history):
    repo, (c0, c1, c2, c3, c4), entry = history

    landings = gate.entry_landings(repo.root, "HEAD")

    assert landings == {_key(entry): (c1, 2)}  # c2 and c3 touch schemas/, the docs commit c4 does not
    assert gate.entry_landings(repo.root, c1) == {_key(entry): (c1, 0)}
    assert gate.entry_landings(repo.root, c0) == {}


def test_a_refreshed_entry_is_a_new_entry_landing_at_the_refresh(history):
    repo, (c0, c1, c2, c3, c4), entry = history
    refreshed = _entry("/properties/b", B, reason="a hand refresh")
    refreshed["after"] = {"type": "string", "minLength": 1}
    c5 = repo.commit("hand refresh", {DELTAS: _deltas(_line(refreshed))})

    landings = gate.entry_landings(repo.root, "HEAD")

    assert landings == {_key(refreshed): (c5, 0)}


def test_an_entry_removed_and_added_again_lands_at_the_re_adding_commit(history):
    repo, (c0, c1, c2, c3, c4), entry = history
    repo.commit("prune", {DELTAS: _deltas()})
    c6 = repo.commit("re-add", {DELTAS: _deltas(_line(entry))})

    assert gate.entry_landings(repo.root, "HEAD") == {_key(entry): (c6, 0)}


def test_only_l1_entries_of_the_base_file_are_marked_merged_and_an_in_flight_one_is_not(history):
    repo, (c0, c1, c2, c3, c4), entry = history
    in_flight = _entry("/properties/c", B)
    l3 = {"layer": "L3", "probe": "p", "before": None, "after": {"code": "E"}, "reason": "r", "test": "t"}
    c5 = repo.commit("a baseline-layer entry and a second PR's entry", {DELTAS: _deltas(_line(entry), _line(l3))})
    path = repo.root / DELTAS
    path.write_text(_deltas(_line(entry), _line(l3), _line(in_flight)), encoding="utf-8")

    deltas = gate.load_deltas(path)
    gate.mark_merged(repo.root, "HEAD", deltas)

    # The L1 entry keeps its landing commit although a later commit also touched the file; an L3 entry is never merged.
    merged = {item.pointer or item.subject: (item.merged, item.landing, item.age) for item in deltas}
    assert merged == {"/properties/b": (True, c1, 2), "p": (False, None, None), "/properties/c": (False, None, None)}
    assert c5 != c1


def test_a_merge_counts_once_however_many_commits_its_branch_had(history):
    repo, (c0, c1, c2, c3, c4), entry = history
    repo.git("switch", "-q", "-c", "side", c4)
    repo.commit("side one", {f"schemas/{OTHER}": _schema(OTHER, x=B, y=B, z=B)})
    repo.commit("side two", {f"schemas/{OTHER}": _schema(OTHER, x=B, y=B, z=B, w=B)})
    repo.git("switch", "-q", "main")
    repo.git("merge", "-q", "--no-ff", "-m", "merge the side branch", "side")

    assert gate.entry_landings(repo.root, "HEAD") == {_key(entry): (c1, 3)}  # c2, c3 and the one merge commit


# --- stale entries and the age gate -------------------------------------------------------------------

def _merged(age: int, *, applied: bool = False, layer: str = "L1") -> gate.Delta:
    return gate.Delta(layer, THING, "/properties/b", gate._MISSING, B, "r", "t", merged=True, landing="abcdef012345",
                      age=age, applied=applied)


def test_a_stale_entry_is_a_note_within_one_later_merge_and_a_failure_beyond_it():
    assert gate.STALE_MERGE_LIMIT == 1
    failures, notes = gate.stale_findings([_merged(0), _merged(1)])
    assert failures == [] and len(notes) == 2 and "abcdef01" in notes[0] and "--prune-stale" in notes[0]
    failures, notes = gate.stale_findings([_merged(2)])
    assert len(failures) == 1 and "limit 1" in failures[0] and notes == []


def test_an_entry_that_still_applies_an_in_flight_entry_and_a_baseline_layer_entry_are_never_stale():
    in_flight = dataclasses.replace(_merged(9), merged=False)
    assert gate.stale_findings([_merged(9, applied=True), in_flight, _merged(9, layer="L3")]) == ([], [])


def _trees(**properties):
    return {THING: _document(THING, **properties)}


def test_a_merged_entry_the_base_moved_past_is_not_a_does_not_apply_failure_but_an_unmerged_one_still_is():
    pointer = "/properties/b"
    base, head = _trees(b={"type": "integer"}), _trees(b={"type": "integer"}, c=B)
    entry = gate.Delta("L1", THING, pointer, gate._MISSING, B, "r", "t")  # neither absent nor B at the base

    rows = {row.schema: row for row in gate.compare_l1(gate.fingerprint_schemas(base), gate.fingerprint_schemas(head), [entry])}
    assert rows[THING].status == "changed" and "does not apply" in rows[THING].detail

    stale = dataclasses.replace(entry, merged=True, landing="x", age=0)
    rows = {row.schema: row for row in gate.compare_l1(gate.fingerprint_schemas(base), gate.fingerprint_schemas(head), [stale])}
    assert rows[THING].status == "additive" and not stale.applied  # the real change is still judged on its own


def test_a_stale_entry_never_excuses_a_real_change():
    pointer = "/properties/b"
    base, head = _trees(b={"type": "integer"}), _trees(b={"type": "string", "minLength": 2})
    stale = gate.Delta("L1", THING, pointer, {"type": "integer"}, {"type": "string", "minLength": 2}, "r", "t",
                       merged=True, landing="x", age=0)
    bad = dataclasses.replace(stale, before={"type": "number"})  # does not apply, and must not excuse anything either

    ok = gate.compare_l1(gate.fingerprint_schemas(base), gate.fingerprint_schemas(head), [stale])
    assert [row.status for row in ok if row.schema == THING] == ["delta"] and stale.applied  # applying still works
    rows = gate.compare_l1(gate.fingerprint_schemas(base), gate.fingerprint_schemas(head), [bad])
    assert [row.status for row in rows if row.schema == THING] == ["changed"]


# --- pruning, with proof ------------------------------------------------------------------------------

def test_prune_removes_the_proven_stale_entry_and_leaves_every_other_line_byte_for_byte(history):
    repo, _, entry = history
    in_flight = _entry("/properties/c", B)
    l3 = {"layer": "L3", "probe": "p", "before": None, "after": {"code": "E"}, "reason": "r", "test": "t"}
    path = repo.root / DELTAS
    path.write_text(_deltas(_line(entry), _line(l3), _line(in_flight)), encoding="utf-8")

    result = gate.prune_stale(repo.root, "HEAD")

    assert [item.pointer for item in result.removed] == ["/properties/b"] and result.kept == []
    assert path.read_text(encoding="utf-8") == _deltas(_line(l3), _line(in_flight))


def test_prune_keeps_an_entry_whose_before_still_holds_at_the_base(history):
    repo, _, entry = history
    never_landed = _entry("/properties/zzz", B)  # in the base file, but the schema never gained it
    repo.commit("an entry for a change that never landed", {DELTAS: _deltas(_line(entry), _line(never_landed))})

    result = gate.prune_stale(repo.root, "HEAD")

    assert [item.pointer for item in result.removed] == ["/properties/b"]
    assert [(item.pointer, "still holds" in reason) for item, reason in result.kept] == [("/properties/zzz", True)]
    assert "/properties/zzz" in (repo.root / DELTAS).read_text(encoding="utf-8")


def test_prune_keeps_an_entry_that_was_not_true_at_its_landing_commit(history):
    repo, _, entry = history
    wrong = _entry("/properties/b", {"type": "number"}, before={"type": "boolean"})  # neither value ever held
    repo.commit("a wrong entry", {DELTAS: _deltas(_line(entry), _line(wrong))})

    result = gate.prune_stale(repo.root, "HEAD")

    assert [item.pointer for item in result.removed] == ["/properties/b"]
    assert len(result.kept) == 1 and "neither its before nor its after" in result.kept[0][1]


def test_prune_keeps_an_entry_whose_after_does_not_hold_at_its_landing_commit(history):
    repo, _, entry = history
    # Recorded for a change that did not come with it (q is absent at the parent and at the landing commit), and q
    # is something else by the base: `before` held where it was recorded, `after` never did.
    unlanded = _entry("/properties/q", {"type": "number"})
    repo.commit("an entry whose change is not in the commit", {DELTAS: _deltas(_line(entry), _line(unlanded))})
    repo.commit("q arrives later, as an integer", {f"schemas/{THING}": _schema(b=B, q={"type": "integer"})})

    result = gate.prune_stale(repo.root, "HEAD")

    assert [item.pointer for item in result.removed] == ["/properties/b"]
    assert len(result.kept) == 1 and "after value does not hold at the landing commit" in result.kept[0][1]


def test_prune_explains_restatement_after_an_overlapping_schema_merge(tmp_path):
    repo = Repo(tmp_path)
    before, after, later = ({"enum": ["old"]}, {"enum": ["old", "new"]}, {"enum": ["latest"]})
    parent = repo.commit("base", {f"schemas/{THING}": _schema(b=before), DELTAS: _deltas()})
    # The after-state is real, but before was captured mid-implementation rather than at the landing parent.
    wrong = _entry("/properties/b", after, before={"enum": ["intermediate"]})
    landing = repo.commit("schema with an inaccurate record", {
        f"schemas/{THING}": _schema(b=after), DELTAS: _deltas(_line(wrong))})
    repo.git("checkout", "-q", "-b", "later-schema")
    repo.commit("later overlapping schema edit", {f"schemas/{THING}": _schema(b=later)})
    repo.git("checkout", "-q", "main")
    repo.git("merge", "--no-ff", "-q", "later-schema", "-m", "later overlapping schema merge")

    result = gate.prune_stale(repo.root, "HEAD")

    assert result.removed == []
    reason = result.kept[0][1]
    assert parent[:8] in reason and landing[:8] in reason
    assert THING in reason and "/properties/b" in reason
    assert "before merging, restate the recorded before/after" in reason
    assert "already merged, so manually retire it only after verifying" in reason
    assert "Rewriting a merged entry changes its landing identity" in reason
    assert "cannot repair its --prune-stale proof" in reason
    assert (repo.root / DELTAS).read_text() == _deltas(_line(wrong))
    corrected = _entry("/properties/b", after, before=before)
    # The corrected landing values prove the historical transition even though today's value differs.
    assert gate._applies(gate.fingerprint_schemas(gate.load_schema_rev(repo.root, parent)).trees,
                         gate.parse_deltas(_deltas(_line(corrected)).encode(), label="corrected")[0])
    assert gate._landed(gate.fingerprint_schemas(gate.load_schema_rev(repo.root, landing)).trees,
                       gate.parse_deltas(_deltas(_line(corrected)).encode(), label="corrected")[0])


def test_prune_retires_a_repair_entry_whose_result_already_held_where_it_was_recorded(history):
    repo, (c0, c1, c2, c3, c4), entry = history
    already = _entry("/properties/b", B, before={"type": "boolean"})  # recorded after B had landed
    repo.commit("repair", {DELTAS: _deltas(_line(entry), _line(already))})

    result = gate.prune_stale(repo.root, "HEAD")

    assert sorted(item.before is gate._MISSING for item in result.removed) == [False, True] and result.kept == []


def test_prune_retires_a_removed_and_an_added_file_marker(tmp_path):
    repo = Repo(tmp_path)
    removed = {"schema": "gone-v0.1.schema.yaml", "pointer": "", "after": "removed", "reason": "r", "test": "t"}
    added = {"schema": "new-v0.1.schema.yaml", "pointer": "", "after": "added", "reason": "r", "test": "t"}
    repo.commit("base", {f"schemas/{THING}": _schema(), "schemas/gone-v0.1.schema.yaml": _schema("gone-v0.1.schema.yaml"), DELTAS: _deltas()})
    (repo.root / "schemas/gone-v0.1.schema.yaml").unlink()
    repo.commit("PR", {f"schemas/{THING}": _schema(), "schemas/new-v0.1.schema.yaml": _schema("new-v0.1.schema.yaml"),
                       DELTAS: _deltas(_line(removed), _line(added))})
    still_there = _entry("", "removed", schema=THING)  # the schema it names still exists
    repo.commit("bogus", {DELTAS: _deltas(_line(removed), _line(added), _line(still_there))})

    result = gate.prune_stale(repo.root, "HEAD")

    assert sorted(item.subject for item in result.removed) == ["gone-v0.1.schema.yaml", "new-v0.1.schema.yaml"]
    assert [item.subject for item, _ in result.kept] == [THING]


def test_prune_keeps_a_removal_marker_whose_schema_was_still_there_at_the_landing_commit(tmp_path):
    repo = Repo(tmp_path)
    marker = {"schema": OTHER, "pointer": "", "after": "removed", "reason": "r", "test": "t"}
    repo.commit("base", {f"schemas/{THING}": _schema(), f"schemas/{OTHER}": _schema(OTHER), DELTAS: _deltas()})
    repo.commit("an entry for a removal that is not in the commit", {DELTAS: _deltas(_line(marker))})
    (repo.root / f"schemas/{OTHER}").unlink()
    repo.commit("the schema goes later", {})

    result = gate.prune_stale(repo.root, "HEAD")

    assert result.removed == [] and len(result.kept) == 1
    assert "after value does not hold at the landing commit" in result.kept[0][1]


def test_prune_without_a_stale_entry_changes_nothing(history):
    repo, _, entry = history
    path = repo.root / DELTAS
    in_flight = _line(_entry("/properties/c", B))
    path.write_text(_deltas(in_flight), encoding="utf-8")

    result = gate.prune_stale(repo.root, "HEAD")

    assert result.removed == [] and path.read_text(encoding="utf-8") == _deltas(in_flight)


def test_a_pr_field_is_optional_must_be_a_positive_integer_and_changes_no_identity():
    with_pr = gate.parse_deltas(_deltas(_line(_entry("/p", B, pr=584))).encode(), label="t")[0]
    without = gate.parse_deltas(_deltas(_line(_entry("/p", B))).encode(), label="t")[0]
    assert with_pr.pr == 584 and without.pr is None and gate.delta_key(with_pr) == gate.delta_key(without)
    for bad in (0, -1, "584", True):
        with pytest.raises(gate.GateError, match="E_EQUIV_DELTAS_ENTRY"):
            gate.parse_deltas(_deltas(_line(_entry("/p", B, pr=bad))).encode(), label="t")


def test_prune_stale_needs_a_base_revision():
    with pytest.raises(SystemExit):
        gate.main(["--prune-stale"])


# --- the gate run ---------------------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _no_inventory(monkeypatch):
    """The synthetic repository has no schema inventory; the lifecycle is what is under test."""
    monkeypatch.setattr(gate, "validate_inventory", lambda *args, **kwargs: ())


def _stale(report: gate.GateReport) -> tuple[list[str], list[str]]:
    return ([item for item in report.failures if "stale expected-delta" in item],
            [item for item in report.notes if "stale expected-delta" in item])


def test_a_base_rev_run_fails_on_an_entry_stale_for_two_schema_merges(history):
    repo, (c0, c1, c2, c3, c4), _ = history

    failures, notes = _stale(gate.run_gate(repo.root, layers=("L1",), base_rev=c0))
    assert failures == [] and notes == []  # the entry is this change's own: it applies and is used

    failures, notes = _stale(gate.run_gate(repo.root, layers=("L1",), base_rev=c1))
    assert failures == [] and len(notes) == 1  # landed in the base itself, no later merge

    failures, notes = _stale(gate.run_gate(repo.root, layers=("L1",), base_rev=c2))
    assert failures == [] and len(notes) == 1  # one later schema merge is allowed

    report = gate.run_gate(repo.root, layers=("L1",), base_rev=c4)
    failures, notes = _stale(report)
    assert len(failures) == 1 and notes == [] and "limit 1" in failures[0]  # c2 and c3 are two
    assert not [item for item in report.notes if "unused" in item]  # reported once, as stale


def test_a_run_without_a_base_revision_treats_every_entry_as_in_flight(history):
    repo, _, _ = history

    report = gate.run_gate(repo.root, layers=("L1",), base_schemas=gate.load_schema_dir(repo.root / "schemas"))

    assert _stale(report) == ([], [])


def test_an_entry_the_base_moved_past_is_not_a_does_not_apply_failure_but_its_real_change_is_judged(history):
    repo, _, _ = history
    # A later PR changed the same pointer; this run adds a different change elsewhere in the same schema.
    repo.commit("someone changes b again", {f"schemas/{THING}": _schema(b={"type": "integer"})})
    base = repo.git("rev-parse", "HEAD")
    repo.commit("this PR adds c", {f"schemas/{THING}": _schema(b={"type": "integer"}, c=B)})

    report = gate.run_gate(repo.root, layers=("L1",), base_rev=base)

    assert not [item for item in report.failures if "does not apply" in item]
    assert _stale(report)[0]  # still reported, and failing by age
    assert any(row.schema == THING and row.status == "additive" for row in report.l1)

