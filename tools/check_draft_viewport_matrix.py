"""Batch all committed corpus views through narrow Draft Layout completion."""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory

import yaml

from chrona.presentation.model.closure import resolve_draft_render
from chrona.resources import safe_load
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.render_review import RenderRequest, render_review


ROOT = Path(__file__).resolve().parents[1]
VIEWPORTS = ((1600, 900), (800, 450), (600, 340))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", action="store_true", help="exercise each actual chrona render exit code")
    args = parser.parse_args()
    failures: list[str] = []
    completed = 0
    warning_count = 0
    for context_path in sorted(ROOT.glob("examples/*/contexts/*.yaml")):
        example = context_path.parent.parent
        context = safe_load(context_path.read_bytes())["body"]
        inputs = context.get("inputs", {})
        with TemporaryDirectory(prefix="chrona-457-fonts-") as directory:
            descriptor = Path(directory) / "font-metrics.yaml"
            descriptor.write_text(yaml.safe_dump(context["environment"]["fontMetrics"]), encoding="utf-8")

            def resource(name: str) -> Path:
                return example / context[name]["address"]

            def optional(name: str) -> Path | None:
                return example / inputs[name]["address"] if name in inputs else None

            icon_catalogs = tuple(
                ((ROOT / "src/chrona/resources" / item["address"])
                 if item.get("store", {}).get("provider") == "package"
                 and item.get("store", {}).get("identity") == "chrona.resources"
                 else example / item["address"])
                for item in inputs.get("iconCatalogs", ()))

            for viewport in VIEWPORTS:
                identifier = f"{example.name}/{context_path.stem}@{viewport[0]}x{viewport[1]}"
                try:
                    if args.cli:
                        output = Path(directory) / f"render-{viewport[0]}x{viewport[1]}.svg"
                        command = [str(Path(sys.executable).parent / "chrona"), "render", str(resource("project")),
                                   "--view", str(resource("view")), "--theme", str(resource("theme")),
                                   "--scheme", str(resource("colorScheme")), "--layout", str(resource("layout")),
                                   "--font-metrics", str(descriptor), "--viewport", f"{viewport[0]}x{viewport[1]}",
                                   "--locale", context["environment"]["locale"],
                                   "--visual-profile", context["target"]["visualProfile"],
                                   "--output", str(output)]
                        for flag, name in (("--actual", "actual"), ("--summary", "summaryProfile"),
                                           ("--detail", "detailProfile")):
                            value = optional(name)
                            if value is not None:
                                command.extend((flag, str(value)))
                        for catalog in icon_catalogs:
                            command.extend(("--icon-catalog", str(catalog)))
                        result = subprocess.run(command, capture_output=True, text=True, check=False)
                        if result.returncode != 0:
                            raise RuntimeError(f"chrona render exit={result.returncode}: {result.stderr or result.stdout}")
                        artifact = output.read_bytes()
                        warning_count += (result.stdout + result.stderr).count("W_LAYOUT_")
                        assert artifact.startswith(b"<svg "), "no SVG artifact"
                        assert re.search(rb'viewBox="([^\"]+)"', artifact), "SVG lacks completed viewBox"
                        completed += 1
                        continue
                    draft = resolve_draft_render(
                        project_path=resource("project"), view_path=resource("view"),
                        theme_path=resource("theme"), scheme_path=resource("colorScheme"),
                        layout_path=resource("layout"), actual_path=optional("actual"),
                        summary_path=optional("summaryProfile"), detail_path=optional("detailProfile"),
                        icon_catalog_paths=icon_catalogs,
                        font_metrics_path=descriptor, viewport=viewport,
                        locale=context["environment"]["locale"],
                        visual_profile=context["target"]["visualProfile"],
                    )
                    rendered = render_review(RenderRequest(
                        draft.closure, draft.asset_root, ReferenceScheduler(),
                        asset_root=draft.asset_root, draft_auto_block=draft.auto_block,
                    ))
                    assert rendered.artifact.content.startswith(b"<svg "), "no SVG artifact"
                    view_box = re.search(rb'viewBox="([^\"]+)"', rendered.artifact.content)
                    assert view_box is not None, "SVG lacks completed viewBox"
                    serialized_bounds = tuple(float(value) for value in view_box.group(1).split())
                    assert len(serialized_bounds) == 4
                    assert all(abs(actual - serialized) < .0011 for actual, serialized in
                               zip(rendered.surface.canvas_bounds, serialized_bounds, strict=True)), (
                        "SVG viewBox differs from completed Layout canvas")
                    completed += 1
                    warning_count += len(rendered.surface.fit_warnings)
                except Exception as error:
                    failures.append(f"{identifier}: {type(error).__name__}: {error}")
    for failure in failures:
        print(failure)
    print(f"draft viewport matrix ({'CLI' if args.cli else 'API'}): {completed}/{completed + len(failures)} rendered; "
          f"{warning_count} fit warnings; {len(failures)} failures")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
