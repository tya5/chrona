"""Export every bundled appearance and compile the unchanged Typst/TikZ sources."""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Mapping

from chrona.usecases.preset_library import list_builtin_presets


ROOT = Path(__file__).resolve().parents[1]
VISUAL_PROFILE = "chrona-output/visual/v0.5-baseline"
TARGETS = {
    "typst": {"engine": "typst", "version": "0.15.1", "grammar": "chrona-typst/v0.1",
              "suffix": ".typ", "pdf": "typst", "version_args": ["--version"]},
    "tikz": {"engine": "tectonic", "version": "0.17.0", "grammar": "chrona-tikz/v0.1",
             "suffix": ".tex", "pdf": "tectonic", "version_args": ["--version"]},
}
TIMEOUT_SECONDS = {"version": 30, "export": 300, "compile": 600}
_SEMVER = re.compile(r"(?<![\d.])(\d+\.\d+\.\d+)(?![\d.])")


def _write_log(path: Path, stdout: str, stderr: str) -> None:
    path.with_suffix(path.suffix + ".stdout.log").write_text(stdout or "", encoding="utf-8")
    path.with_suffix(path.suffix + ".stderr.log").write_text(stderr or "", encoding="utf-8")


def _error(kind: str, message: str) -> dict[str, str]:
    return {"type": kind, "message": message}


def _run(runner: Callable[..., Any], command: list[str], *, cwd: Path,
         phase: str, env: Mapping[str, str] | None = None) -> tuple[Any | None, dict[str, str] | None]:
    try:
        options: dict[str, Any] = {"cwd": cwd, "capture_output": True, "text": True,
                                   "timeout": TIMEOUT_SECONDS[phase]}
        if env is not None:
            options["env"] = dict(env)
        return runner(command, **options), None
    except subprocess.TimeoutExpired as exc:
        return None, _error(f"{phase}_timeout", f"{phase} exceeded {TIMEOUT_SECONDS[phase]} seconds: {exc}")
    except OSError as exc:
        return None, _error(f"{phase}_error", f"could not execute {command[0]}: {exc}")


def _check_version(target: str, executable: Path, outdir: Path,
                   runner: Callable[..., Any]) -> dict[str, Any]:
    settings = TARGETS[target]
    result, error = _run(runner, [str(executable), *settings["version_args"]],
                         cwd=ROOT, phase="version")
    entry: dict[str, Any] = {"expected": settings["version"], "observed": None,
                             "error": error}
    if error:
        _write_log(outdir / f"{target}-version.log", "", error["message"])
        return entry
    raw = (result.stdout or "") + "\n" + (result.stderr or "")
    _write_log(outdir / f"{target}-version.log", result.stdout or "", result.stderr or "")
    match = _SEMVER.search(raw)
    entry["observed"] = match.group(1) if match else None
    if result.returncode != 0:
        entry["error"] = _error("version_error", f"version command exited {result.returncode}")
    elif not match:
        entry["error"] = _error("version_error", "version output contains no semantic version")
    elif match.group(1) != settings["version"]:
        entry["error"] = _error("version_error", f"expected {settings['version']}, found {match.group(1)}")
    return entry


def _slug(value: str) -> str:
    result = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-.")
    return result or "preset"


def _export_command(target: str, executable_python: str, project: Path,
                    actual: Path | None, preset: str | None, output: Path) -> list[str]:
    settings = TARGETS[target]
    command = [executable_python, "-m", "chrona", "render", str(project),
               "--format", target, "--visual-profile", VISUAL_PROFILE,
               "--typesetter-engine", settings["engine"],
               "--typesetter-version", settings["version"],
               "--typesetter-adapter-grammar", settings["grammar"],
               "--output", str(output)]
    if actual is not None:
        command.extend(("--actual", str(actual)))
    if preset is not None:
        command.extend(("--preset", preset))
    return command


def _compile_command(target: str, executable: Path, source: Path, pdf: Path) -> tuple[list[str], Path, Path]:
    if target == "typst":
        fonts = ROOT / "src" / "chrona" / "resources" / "fonts"
        return ([str(executable), "compile", "--font-path", str(fonts), str(source), str(pdf)],
                source.parent, pdf)
    return ([str(executable), "--outdir", str(pdf.parent), "--keep-logs", str(source)],
            source.parent, pdf)


def _write_fontconfig(output: Path) -> tuple[Path, Path]:
    """Keep Tectonic's font discovery local to bundled Chrona assets and this run."""
    font_dir = ROOT / "src" / "chrona" / "resources" / "fonts"
    config_dir = output / "fontconfig"
    cache_dir = config_dir / "cache"
    config_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    config = config_dir / "fonts.conf"
    config.write_text(
        "<?xml version=\"1.0\"?>\n"
        "<!DOCTYPE fontconfig SYSTEM \"fonts.dtd\">\n"
        "<fontconfig>\n"
        f"  <dir>{html.escape(str(font_dir))}</dir>\n"
        f"  <cachedir>{html.escape(str(cache_dir))}</cachedir>\n"
        "</fontconfig>\n",
        encoding="utf-8",
    )
    return config, font_dir


def run_matrix(*, typst: Path, tectonic: Path, output: Path,
               project: Path, actual: Path | None = None,
               runner: Callable[..., Any] | None = None) -> dict[str, Any]:
    """Run all preset/target cases, retaining sources, logs, PDFs and a JSON report."""
    run = runner or subprocess.run
    output = output.resolve()
    project = project.resolve()
    actual = actual.resolve() if actual is not None else None
    output.mkdir(parents=True, exist_ok=True)
    fontconfig_file, _font_dir = _write_fontconfig(output)
    tectonic_env = os.environ.copy()
    tectonic_env["FONTCONFIG_FILE"] = str(fontconfig_file)
    executables = {"typst": typst.resolve(), "tikz": tectonic.resolve()}
    versions = {target: _check_version(target, executable, output, run)
                for target, executable in executables.items()}
    presets: list[str | None] = [None, *(str(item["id"]) for item in list_builtin_presets())]
    cases: list[dict[str, Any]] = []

    for target, settings in TARGETS.items():
        for preset in presets:
            name = "default" if preset is None else _slug(preset)
            case_dir = output / target / name
            case_dir.mkdir(parents=True, exist_ok=True)
            stem = f"{name}-{target}"
            source = case_dir / f"{stem}{settings['suffix']}"
            pdf = case_dir / f"{stem}.pdf"
            case: dict[str, Any] = {"target": target, "preset": preset, "status": "failed",
                                   "source": str(source), "pdf": str(pdf), "error": None}
            cases.append(case)
            if versions[target]["error"]:
                case["error"] = versions[target]["error"]
                continue
            if source.exists() or pdf.exists():
                case["error"] = _error("output_exists", "refusing to replace a pre-existing source or PDF artifact")
                continue

            command = _export_command(target, sys.executable, project, actual, preset, source)
            result, error = _run(run, command, cwd=ROOT, phase="export")
            if error:
                _write_log(case_dir / f"{stem}-export", "", error["message"])
                case["error"] = error
                continue
            _write_log(case_dir / f"{stem}-export", result.stdout or "", result.stderr or "")
            try:
                payload = json.loads(result.stdout)
            except (TypeError, json.JSONDecodeError):
                case["error"] = _error("protocol_error", "render export did not emit valid JSON on stdout")
                continue
            if not isinstance(payload, dict) or not isinstance(payload.get("status"), str) or not isinstance(payload.get("diagnostics"), list):
                case["error"] = _error("protocol_error", "render export JSON is missing status or diagnostics")
                continue
            if any(not isinstance(item, dict) or not isinstance(item.get("code"), str)
                   or not isinstance(item.get("message"), str) for item in payload["diagnostics"]):
                case["error"] = _error("protocol_error", "render export diagnostics have an unknown shape")
                continue
            if result.returncode != 0:
                expected_exit = {"rejected": 1, "failed": 2}.get(payload["status"])
                if expected_exit is None or result.returncode != expected_exit:
                    case["error"] = _error("protocol_error", "render failure status and exit code disagree")
                    continue
                case["error"] = _error("export_error", f"render export exited {result.returncode}: {payload}")
                continue
            if payload["status"] != "ok":
                case["error"] = _error("protocol_error", "render export exited successfully without status=ok")
                continue
            if not source.is_file() or source.stat().st_size == 0:
                case["error"] = _error("missing_artifact", "successful render export produced no non-empty source")
                continue

            compile_command, compile_cwd, expected_pdf = _compile_command(target, executables[target], source, pdf)
            result, error = _run(run, compile_command, cwd=compile_cwd, phase="compile",
                                 env=tectonic_env if target == "tikz" else None)
            if error:
                _write_log(case_dir / f"{stem}-compile", "", error["message"])
                case["error"] = error
                continue
            _write_log(case_dir / f"{stem}-compile", result.stdout or "", result.stderr or "")
            if result.returncode != 0:
                case["error"] = _error("compiler_error", f"compiler exited {result.returncode}")
                continue
            if not expected_pdf.is_file() or expected_pdf.stat().st_size == 0:
                case["error"] = _error("missing_artifact", "compiler succeeded without a non-empty PDF")
                continue
            case["status"] = "compiled"
            case["error"] = None

    status = "failed" if any(case["status"] == "failed" for case in cases) else "complete"
    report = {"status": status, "visual_profile": VISUAL_PROFILE,
              "project": str(project), "actual": str(actual) if actual else None,
              "versions": versions, "case_count": len(cases), "cases": cases}
    (output / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--typst", type=Path, required=True, help="Typst 0.15.1 executable")
    parser.add_argument("--tectonic", type=Path, required=True, help="Tectonic 0.17.0 executable")
    parser.add_argument("--output", type=Path, required=True, help="directory for sources, logs, PDFs and report.json")
    parser.add_argument("--project", type=Path, required=True, help="Draft Project YAML to render")
    parser.add_argument("--actual", type=Path, help="optional Actual Set YAML")
    args = parser.parse_args(argv)
    report = run_matrix(typst=args.typst, tectonic=args.tectonic, output=args.output,
                        project=args.project, actual=args.actual)
    print(json.dumps({"status": report["status"], "case_count": report["case_count"],
                      "report": str(args.output.resolve() / "report.json")}, ensure_ascii=False))
    return 0 if report["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
