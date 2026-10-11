"""Non-gating #1298 CLI measurements; run as a module in the project venv."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import yaml

from tests.support.routing_scale import routing_scale_project


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if not hasattr(os, "wait4"):
        parser.error("per-child CPU/RSS measurement requires POSIX wait4")
    root = args.output_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    cli = Path(sys.executable).with_name("chrona")
    records = []
    for size, relation_count in ((200, 46), (1000, 228)):
        project = routing_scale_project(size)
        assert len(project["objects"]) == size
        assert len(project["relations"]) == relation_count
        source = root / f"scale-{size}.yaml"
        with source.open("x", encoding="utf-8") as stream:
            yaml.safe_dump(project, stream, sort_keys=False)
        hashes = []
        for repeat in (1, 2):
            directory = root / f"scale-{size}-run-{repeat}"
            directory.mkdir()
            svg, scene = directory / "review.svg", directory / "review.scene.json"
            argv = [str(cli), "render", str(source), "-o", str(svg),
                    "--emit-scene", str(scene)]
            print(f"START {size}/{relation_count} run {repeat}", flush=True)
            started = time.monotonic()
            with (directory / "stdout.json").open("wb") as stdout, \
                    (directory / "stderr.txt").open("wb") as stderr:
                process = subprocess.Popen(argv, stdout=stdout, stderr=stderr)
                _, status, usage = os.wait4(process.pid, 0)
                process.returncode = os.waitstatus_to_exitcode(status)
            record = {
                "objects": size, "relations": relation_count, "repeat": repeat,
                "argv": argv, "exit": process.returncode,
                "wallSeconds": time.monotonic() - started,
                "cpuUserSeconds": usage.ru_utime,
                "cpuSystemSeconds": usage.ru_stime,
                "peakRssBytes": usage.ru_maxrss * (1 if sys.platform == "darwin" else 1024),
            }
            if process.returncode == 0:
                report = json.loads((directory / "stdout.json").read_text())
                assert report["status"] == "ok" and not report["diagnostics"]
                record["warningCodes"] = dict(Counter(w["code"] for w in report["warnings"]))
                record["sha256"] = {
                    path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in (svg, scene)
                }
                hashes.append(record["sha256"])
            records.append(record)
            (root / "measurements.json").write_text(
                json.dumps(records, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(record, sort_keys=True), flush=True)
            if process.returncode != 0:
                return process.returncode
        assert hashes[0] == hashes[1], f"{size}: repeated Scene/SVG bytes differ"
        print(f"IDENTICAL {size}: Scene/SVG", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
