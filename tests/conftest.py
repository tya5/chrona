"""Session fixtures shared across the test tree."""
from __future__ import annotations

import os

import pytest

from tests.support.render_cache import RenderCache


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--longest-first",
        action="store_true",
        default=False,
        help="order the selected items by recorded duration, longest first (#721)",
    )


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Start the longest items first so that no worker begins one near the end (#721).

    Runs after pytest-split's selection.  The key is deterministic (recorded duration,
    then node id), so every xdist worker computes the same order.  An id with no
    recorded duration sorts as a short item.
    """
    if not config.getoption("--longest-first"):
        return
    import json
    from pathlib import Path

    path = Path(str(config.rootpath)) / ".test_durations"
    try:
        recorded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    items.sort(key=lambda item: (-float(recorded.get(item.nodeid, 0.0)), item.nodeid))


@pytest.fixture(scope="session")
def render_cache(tmp_path_factory: pytest.TempPathFactory) -> RenderCache:
    """One render per (project, actual, preset, flags) for the whole pytest run (#657).

    Use it only for unmodified committed inputs.  Under xdist each worker has its own
    ``basetemp``; the parent directory is shared by all workers of the run, so the cache
    lives there and a combination is rendered once across workers, not once per worker.
    """
    base = tmp_path_factory.getbasetemp()
    if os.environ.get("PYTEST_XDIST_WORKER"):
        base = base.parent
    return RenderCache(base / "chrona-render-cache")
