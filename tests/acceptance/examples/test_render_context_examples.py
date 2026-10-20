"""Generated example Contexts are complete and bind exact reusable resources."""
from hashlib import sha256
from pathlib import Path

import yaml

from chrona.resources import schema_resource, validator_for_schema
from chrona.presentation.model.font_resources import resolve_font_resource
from tests.support.deck_contexts import context_document


ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = ROOT / "src/chrona/resources"


def test_current_example_contexts_bind_exact_source_bytes():
    halcyon = ROOT / "examples/halcyon-1"
    sources = [
        ((ROOT / relative).parents[1], yaml.safe_load((ROOT / relative).read_text(encoding="utf-8")))
        for relative in ("tests/fixtures/controller-z/contexts/executive.yaml",
                         "tests/fixtures/aster-ssd/contexts/01-overview.yaml")
    ]
    # HALCYON slides as the manifest selects them: explicit or composed from shared defaults (#415).
    sources += [(halcyon, context_document(halcyon, slide_id)) for slide_id in (
        "mission-brief", "programme-board", "launch-campaign", "gallery-editorial-lanes")]
    for example_root, context in sources:
        version = context["version"].rsplit("/", 1)[-1]
        schema = yaml.safe_load(schema_resource(f"render-context-{version}.schema.yaml").read_text(encoding="utf-8"))
        validator_for_schema(schema).validate(context)
        body = context["body"]
        references = [body[name] for name in ("project", "view", "theme", "colorScheme", "layout")]
        references.extend(body["inputs"].values())
        for reference in references:
            store = reference["store"]
            root = PACKAGE_ROOT if (store["provider"], store["identity"]) == ("package", "chrona.resources") else example_root
            payload = (root / reference["address"]).read_bytes()
            if "contentIdentity" in reference:
                assert reference["contentIdentity"] == "sha256:" + sha256(payload).hexdigest()
        for font_asset in body["environment"]["fontMetrics"]["assets"]:
            for role in ("metrics", "font"):
                record = font_asset.get(role)
                if record is None:
                    continue
                payload = resolve_font_resource(record["locator"], asset_root=example_root).read_bytes()
                if "contentIdentity" in record:
                    assert record["contentIdentity"] == "sha256:" + sha256(payload).hexdigest()
