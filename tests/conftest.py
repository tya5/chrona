"""Session fixtures shared across the test tree."""
from __future__ import annotations

import os

import pytest

from tests.support.render_cache import RenderCache


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
