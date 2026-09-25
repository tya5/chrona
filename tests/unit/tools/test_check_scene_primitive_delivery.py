from tools.check_scene_primitive_delivery import OWNERS, delivery_errors, model_fields


def test_every_public_scene_field_has_one_live_explicit_delivery_owner():
    assert not delivery_errors()
    assert set(model_fields()) == set(OWNERS)


def test_delivery_manifest_covers_each_field_once():
    for name, fields in model_fields().items():
        assert {field for owner in OWNERS[name] for field in owner.fields} == fields
