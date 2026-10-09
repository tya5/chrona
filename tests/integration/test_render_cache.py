"""The shared render cache renders each committed input once and isolates its readers (#657)."""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import pytest

from tests.support.render_cache import (
    RenderCache, RenderCacheError, RenderResult, digest_files, make_key, render_uncached,
)

HALCYON = "examples/halcyon-1/project.yaml"
HALCYON_ACTUAL = "examples/halcyon-1/actual.yaml"


def test_each_render_key_renders_at_most_once(render_cache):
    key = make_key(HALCYON, HALCYON_ACTUAL)
    results = [render_cache.render(HALCYON, HALCYON_ACTUAL) for _ in range(3)]
    counts = render_cache.render_counts()
    assert counts[key.digest] == 1, "three requests for one key must cause exactly one render"
    # The invariant holds at any moment of the run, across every worker and every test so far.
    assert max(counts.values()) <= 1, {render_cache.labels()[digest]: n for digest, n in counts.items() if n > 1}
    assert results[0].svg == results[1].svg == results[2].svg


def test_readers_cannot_change_what_another_reader_sees(render_cache):
    first = render_cache.render(HALCYON, HALCYON_ACTUAL)
    assert first.stderr == ""
    assert json.loads(first.stdout)["status"] == "ok"
    scene = first.scene
    scene["surfaces"].clear()
    warnings = first.warnings
    warnings.append({"code": "X_INJECTED"})
    second = render_cache.render(HALCYON, HALCYON_ACTUAL)
    assert second.scene["surfaces"], "a mutated Scene must not reach the next reader"
    assert {"code": "X_INJECTED"} not in second.warnings
    assert first.scene["surfaces"], "a fresh access parses afresh"
    assert isinstance(second.svg, bytes) and isinstance(second.scene_text, str)


def test_render_result_warnings_parse_stdout_envelope_afresh_without_stderr_fallback():
    warning = {
        "code": "W_LAYOUT_TEXT_ELLIPSIZED", "severity": "warning",
        "sourceRef": "/objects/titlecard", "detail": {"facts": {"requiredInline": 125.5}},
        "occurrences": ["W_LAYOUT_TEXT_ELLIPSIZED:member-label:titlecard:titlecard"],
    }
    result = RenderResult(
        svg=b"<svg/>", scene_text="{}",
        stdout=json.dumps({"status": "ok", "diagnostics": [], "warnings": [warning]}),
        stderr='{"code":"W_LEGACY_STDERR_SHOULD_NOT_BE_READ"}\n',
    )

    warnings = result.warnings
    assert warnings == [warning]
    assert warnings[0]["sourceRef"] == "/objects/titlecard"
    warnings[0]["detail"]["facts"]["requiredInline"] = 0
    warnings[0]["occurrences"].append("mutated")
    warnings.append({"code": "X_INJECTED"})

    assert result.warnings == [warning]


def test_key_covers_every_input_byte_and_every_flag():
    base = make_key(HALCYON, HALCYON_ACTUAL, "print-mono")
    assert base == make_key(HALCYON, HALCYON_ACTUAL, "print-mono")
    assert base != make_key(HALCYON, HALCYON_ACTUAL, "editorial")
    assert base != make_key(HALCYON, None, "print-mono")
    assert base != make_key(HALCYON, HALCYON_ACTUAL, "print-mono", ("--visual-profile", "chrona-output/visual/v0.6-svg"))
    assert base.digest != make_key(HALCYON, HALCYON_ACTUAL, "editorial").digest


def test_digest_changes_when_one_byte_of_an_input_changes(tmp_path):
    first, second = tmp_path / "a.yaml", tmp_path / "b.yaml"
    first.write_bytes(b"one")
    second.write_bytes(b"two")
    before = digest_files([first, second])
    second.write_bytes(b"twp")
    assert digest_files([first, second]) != before


def test_input_outside_committed_roots_is_refused(render_cache, tmp_path):
    project = tmp_path / "project.yaml"
    project.write_text("x: 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="committed inputs"):
        render_cache.render(project)


def test_a_worker_waits_for_a_render_in_progress_instead_of_rendering_twice(tmp_path):
    cache = RenderCache(tmp_path / "cache")
    key = make_key(HALCYON, HALCYON_ACTUAL)
    lock = cache.root / f"{key.digest}.lock"
    lock.write_text("", encoding="utf-8")

    def other_worker() -> None:
        time.sleep(0.3)
        staging = cache.root / f"{key.digest}.tmp"
        staging.mkdir()
        for name, content in (("out.svg", "<svg/>"), ("scene.json", "{}"), ("stdout.txt", ""), ("stderr.txt", "")):
            (staging / name).write_text(content, encoding="utf-8")
        staging.rename(cache.root / key.digest)
        lock.unlink()

    thread = threading.Thread(target=other_worker)
    thread.start()
    result = cache.render(HALCYON, HALCYON_ACTUAL)
    thread.join()
    assert result.svg == b"<svg/>"
    assert cache.render_counts() == {}, "the waiting worker must not have rendered"


def test_a_key_already_logged_is_never_rendered_again(tmp_path):
    cache = RenderCache(tmp_path / "cache")
    key = make_key(HALCYON, HALCYON_ACTUAL)
    (cache.root / "renders.log").write_text(f"{key.digest}\t{key.label}\n", encoding="utf-8")
    with pytest.raises(RenderCacheError, match="second render"):
        cache.render(HALCYON, HALCYON_ACTUAL)
    assert not (cache.root / f"{key.digest}.lock").exists(), "a refused render must release its lock"


def test_two_renders_of_one_input_are_byte_identical(tmp_path):
    """The cache makes one render stand for many, so determinism is asserted explicitly."""
    outputs = []
    for name in ("first", "second"):
        directory: Path = tmp_path / name
        directory.mkdir()
        render_uncached(["render", HALCYON, "--actual", HALCYON_ACTUAL, "--output", str(directory / "out.svg"),
                         "--emit-scene", str(directory / "scene.json")])
        outputs.append(((directory / "out.svg").read_bytes(), (directory / "scene.json").read_bytes()))
    assert outputs[0] == outputs[1]
