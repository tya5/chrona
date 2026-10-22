"""Ephemeral one-pair profiling helper; verification branch only, not product code."""
from __future__ import annotations

import argparse
import contextlib
import cProfile
import hashlib
import inspect
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time


def machine_facts() -> dict:
    return {
        "load": os.getloadavg(), "cpuCount": os.cpu_count(),
        "procStat": Path("/proc/stat").read_text(),
        "processes": subprocess.check_output(["ps", "-eo", "pid,comm,pcpu"], text=True),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worktree", type=Path, required=True)
    parser.add_argument("--trial", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    from chrona.app.cli import main as render_main
    from chrona.presentation.model.render_progress import RenderProgress

    imported_cli = Path(inspect.getfile(render_main)).resolve()
    if not imported_cli.is_relative_to(args.worktree.resolve()):
        raise RuntimeError(f"wrong editable checkout: {imported_cli}")

    args.output.mkdir(parents=True, exist_ok=True)
    files = [args.trial / "plan" / f"A-en-{kind}.yaml"
             for kind in ("project", "actual", "baseline")]
    command = ["chrona", "render", str(files[0]), "--actual", str(files[1]),
               "--snapshot", str(files[2]), "--preset", "target-b", "--locale", "en-US",
               "--output", str(args.output / "A-en.svg"),
               "--emit-scene", str(args.output / "A-en.scene.json"), "--progress"]
    events, writes = [], []
    original_emit = RenderProgress.emit

    def observed_emit(self, event):
        events.append({"time": time.monotonic(), "event": repr(event)})
        return original_emit(self, event)

    class TimedStderr:
        # Actual CLI writes, distinct from buffered/internal progress events.
        def __init__(self, stream):
            self.stream = stream

        def write(self, text):
            writes.append({"time": time.monotonic(), "text": text})
            return self.stream.write(text)

        def flush(self):
            return self.stream.flush()

        def isatty(self):
            return False

    profiler = cProfile.Profile()
    RenderProgress.emit = observed_emit
    before = machine_facts()
    started, cpu_started = time.monotonic(), time.process_time()
    exit_code = 0
    try:
        with (args.output / "cli.stdout").open("w") as stdout, (args.output / "cli.stderr").open("w") as stderr:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(TimedStderr(stderr)):
                sys.argv = command
                profiler.enable()
                try:
                    render_main()
                except SystemExit as error:
                    exit_code = int(error.code or 0)
                finally:
                    profiler.disable()
    except BaseException:
        exit_code = 1
        raise
    finally:
        elapsed, cpu = time.monotonic() - started, time.process_time() - cpu_started
        RenderProgress.emit = original_emit
        after = machine_facts()
        profiler.dump_stats(str(args.output / "profile.pstats"))
        (args.output / "internal-events.json").write_text(json.dumps(events, indent=2) + "\n")
        (args.output / "visible-stderr-writes.json").write_text(json.dumps(writes, indent=2) + "\n")
        receipt = {
            "command": command, "exitCode": exit_code, "wallSeconds": elapsed,
            "cpuSeconds": cpu, "profiling": True,
            "scope": "one render after CLI module import; cProfile enabled for both sources",
            "python": sys.version, "platform": platform.platform(),
            "importedCli": str(imported_cli),
            "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=args.worktree, text=True).strip(),
            "inputSha256": {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in files},
            "machineBefore": before, "machineAfter": after,
        }
        (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt), flush=True)
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
