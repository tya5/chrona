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
    ):
        path = ROOT / relative
        context = yaml.safe_load(path.read_text())
        version = context["version"].rsplit("/", 1)[-1]\n        schema = yaml.safe_load(schema_resource(f"render-context-{version}.schema.yaml").read_text())\n        jsonschema.Draft202012Validator(schema).validate(context)
        body = context["body"]
        references = [body[name] for name in ("project", "view", "theme", "colorScheme", "layout")]
        references.extend(body["inputs"].values())
        example_root = path.parents[1]
        for reference in references:
            payload = (example_root / reference["address"]).read_bytes()
            if "contentIdentity" in reference:
                assert reference["contentIdentity"] == "sha256:" + sha256(payload).hexdigest()
        font = body["environment"]["fontMetrics"]["assets"][0]
        payload = (ROOT / "src/chrona/resources" / font["path"]).read_bytes()
        if "contentIdentity" in font:
            assert font["contentIdentity"] == "sha256:" + sha256(payload).hexdigest()
