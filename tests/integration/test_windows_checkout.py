"""Windows-only checkout evidence for identity-bound public corpus bytes."""
from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(sys.platform != "win32", reason="exercises Git for Windows checkout filtering")
def test_default_autocrlf_clone_reproduces_every_declared_corpus_slide(tmp_path):
    clone = tmp_path / "chrona-crlf-clone"
    subprocess.run(["git", "-c", "core.autocrlf=true", "clone", "--no-local", str(ROOT), str(clone)], check=True)
    environment = {**os.environ, "PYTHONPATH": str(clone / "src")}
    for manifest in sorted(clone.glob("examples/*/manifest.yaml")):
        value = yaml.safe_load(manifest.read_text(encoding="utf-8"))
        for slide in value["slides"]:
            subprocess.run([
                sys.executable, str(clone / "tools/materialize_example.py"), str(manifest),
                "--slide", slide["id"], "--output", str(tmp_path / manifest.parent.name / slide["id"]),
            ], env=environment, check=True)
