"""Generated example Contexts are complete and bind exact reusable resources."""
from hashlib import sha256
from pathlib import Path

import jsonschema
import yaml

from chrona.resources import schema_resource


ROOT = Path(__file__).resolve().parents[3]


def test_current_example_contexts_bind_exact_source_bytes():
    for relative in (
        "examples/controller-z/contexts/executive.yaml",
        "examples/aster-ssd/contexts/01-overview.yaml",
        "examples/halcyon-1/contexts/01-mission-brief.yaml",
        "examples/halcyon-1/contexts/02-programme-board.yaml",
        "examples/halcyon-1/contexts/03-launch-campaign.yaml",
    ):
        path = ROOT / relative
        context = yaml.safe_load(path.read_text())
        version = context["version"].rsplit("/", 1)[-1]
        schema = yaml.safe_load(schema_resource(f"render-context-{version}.schema.yaml").read_text())
        jsonschema.Draft202012Validator(schema).validate(context)
        body = context["body"]
        references = [body[name] for name in ("project", "view", "theme", "colorScheme", "layout")]
        references.extend(body["inputs"].values())
        example_root = path.parents[1]
        for reference in references:
            payload = (example_root / reference["address"]).read_bytes()
            if "contentIdentity" in reference:
                assert reference["contentIdentity"] == "sha256:" + sha256(payload).hexdigest()
        for font_asset in body["environment"]["fontMetrics"]["assets"]:
            for role in ("metrics", "font"):
                record = font_asset[role]
                payload = (ROOT / "src/chrona/resources" / record["path"]).read_bytes()
                assert record["contentIdentity"] == "sha256:" + sha256(payload).hexdigest()
