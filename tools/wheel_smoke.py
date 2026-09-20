"""Exercise installed-wheel behavior without reading repository resources."""
from __future__ import annotations

import sys
from unittest.mock import patch

from chrona.app.cli import main
from chrona.core.validation import validate_project
from chrona.presentation.model.settings import builtin_bases, resolve_presentation_settings
from chrona.scheduling.scheduler import schedule


PROJECT = {
    "version": "timeline/v0.1",
    "project": {"id": "wheel-smoke", "title": "Wheel smoke"},
    "objects": {
        "task": {
            "type": "task",
            "title": "Task",
            "schedule": {
                "mode": "fixed",
                "start": "2026-01-01",
                "end": "2026-01-02",
            },
        }
    },
}


def run() -> None:
    assert validate_project(PROJECT) == []
    assert schedule(PROJECT).ok
    settings = builtin_bases()["executive-v0.2"]
    assert resolve_presentation_settings(settings) == settings
    try:
        with patch.object(sys, "argv", ["chrona", "--help"]):
            main()
    except SystemExit as error:
        assert error.code == 0
    else:
        raise AssertionError("CLI help did not terminate through argparse")
    print("Chrona installed-wheel smoke: PASS")


if __name__ == "__main__":
    run()
