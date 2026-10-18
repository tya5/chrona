#!/usr/bin/env python3
"""Run the pinned trial-8 plain/hinted renders (see trial-summary.json for invocation)."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT: Path | None = None
DESIGNS = ("executive-light", "target-b", "marquee")


def usable(record: dict) -> bool:
    return (record.get("processOutcome") == "returned" and record.get("returnCode") == 0
            and isinstance(record.get("stdoutJson"), dict)
            and record["stdoutJson"].get("status") == "ok"
            and record.get("pngExists") and record.get("sceneExists"))


def digest_paths(argv: list[str]) -> dict[str, str]:
    """Hash input files named in argv; this deliberately excludes implicit inputs."""
    found: dict[str, str] = {}
    for item in argv:
        path = Path(item)
        if path.is_file():
            found[str(path.resolve())] = hashlib.sha256(path.read_bytes()).hexdigest()
    return found


def run_one(chrona: Path, design: str, week: int, variant: str, out: Path,
            previous: Path | None) -> dict:
    wd = ROOT / f"w{week}"
    stem = out / variant / f"{design}-w{week}"
    stem.parent.mkdir(parents=True, exist_ok=True)
    args = [str(chrona), "render", str(wd / "project.yaml"), "--preset",
            str(ROOT / "looks" / design / "preset.yaml"), "--actual", str(wd / "actual.yaml")]
    if design in ("target-b", "marquee") or week == 5:
        args += ["--snapshot", str(wd / "baseline.yaml")]
    if week == 5:
        args += ["--forecast"]
    if previous is not None:
        args += ["--previous-scene", str(previous)]
    args += ["--output", str(stem) + ".png", "--emit-scene", str(stem) + ".scene.json"]
    start = time.perf_counter()
    try:
        result = subprocess.run(args, capture_output=True, text=True, check=False)
        elapsed = time.perf_counter() - start
        try:
            payload = json.loads(result.stdout)
            parse_error = None
        except (json.JSONDecodeError, TypeError) as exc:
            payload = None
            parse_error = f"{type(exc).__name__}: {exc}"
        return {
            "design": design, "week": week, "variant": variant,
            "returnCode": result.returncode, "processOutcome": "returned",
            "elapsedSeconds": elapsed, "argv": args,
            "argvPathSha256": digest_paths(args), "stdoutJson": payload,
            "stdoutRaw": result.stdout, "stdoutParseError": parse_error,
            "stderr": result.stderr,
            "pngExists": Path(str(stem) + ".png").is_file(),
            "sceneExists": Path(str(stem) + ".scene.json").is_file(),
        }
    except OSError as exc:
        return {
            "design": design, "week": week, "variant": variant,
            "returnCode": None, "processOutcome": "spawn-error",
            "elapsedSeconds": time.perf_counter() - start, "argv": args,
            "argvPathSha256": digest_paths(args), "stdoutJson": None,
            "stdoutRaw": "", "stdoutParseError": None,
            "stderr": f"{type(exc).__name__}: {exc}",
            "pngExists": False, "sceneExists": False,
        }


def run_design(chrona: Path, design: str, out: Path) -> list[dict]:
    records: list[dict] = []
    plain_scenes: dict[int, Path] = {}
    for week in range(1, 6):
        rec = run_one(chrona, design, week, "plain", out, None)
        records.append(rec)
        if usable(rec):
            plain_scenes[week] = out / "plain" / f"{design}-w{week}.scene.json"

    # Week one has identical base inputs and no history in both variants, so the
    # plain scene is the hint chain's initial previous-scene artifact.
    previous = plain_scenes.get(1)
    for week in range(1, 6):
        if week == 1:
            if previous is None:
                records.append({"design": design, "week": 1, "variant": "hint",
                                "processOutcome": "reused-plain-w1", "reused": False,
                                "blockedReason": "plain week 1 did not produce a usable Scene"})
                previous = None
                continue
            records.append({"design": design, "week": 1, "variant": "hint",
                            "processOutcome": "reused-plain-w1", "reused": True,
                            "sourceScene": str(previous), "sameBaseInputs": True})
            continue
        if previous is None:
            records.append({"design": design, "week": week, "variant": "hint",
                            "processOutcome": "blocked-missing-previous-scene",
                            "blockedReason": "preceding hinted week produced no usable Scene"})
            continue
        rec = run_one(chrona, design, week, "hint", out, previous)
        records.append(rec)
        current = out / "hint" / f"{design}-w{week}.scene.json"
        previous = current if usable(rec) else None
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", required=True, type=Path,
                        help="Pinned trial-8 directory from bf3940dbe9af487ac6cace5458554762594f3477")
    parser.add_argument("--chrona", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    global ROOT
    ROOT = args.input_root.expanduser().resolve()
    chrona = args.chrona.expanduser().resolve()
    out = args.output_dir.expanduser().resolve()
    if not (ROOT / "w1" / "project.yaml").is_file():
        parser.error(f"trial input directory not found: {ROOT}")
    if not chrona.is_file():
        parser.error(f"Chrona executable not found: {chrona}")
    if out.exists() and any(out.iterdir()):
        parser.error(f"output directory must be absent or empty: {out}")
    out.mkdir(parents=True, exist_ok=True)
    results = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(run_design, chrona, d, out): d for d in DESIGNS}
        for future in as_completed(futures):
            design = futures[future]
            try:
                records = future.result()
            except Exception as exc:  # retain job-level failures in the receipt
                records = [{"design": design, "processOutcome": "runner-error",
                            "error": f"{type(exc).__name__}: {exc}"}]
            results.extend(records)
            for r in records:
                print(json.dumps({k: r.get(k) for k in
                                  ("design", "week", "variant", "processOutcome", "returnCode", "elapsedSeconds")},
                                 sort_keys=True), flush=True)
    receipt = {"inputRoot": str(ROOT), "chrona": str(chrona), "outputRoot": str(out),
               "designConcurrency": 3, "weekOrder": "sequential per design",
               "successMeaning": "processOutcome=returned and returnCode=0 is process success only; inspect stdoutJson.status and artifacts separately",
               "records": results}
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return 0 if all(usable(r) or (r.get("processOutcome") == "reused-plain-w1" and r.get("reused"))
                    for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
