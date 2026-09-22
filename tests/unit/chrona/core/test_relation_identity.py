from chrona.core.relation_identity import relation_identity


def test_relation_identity_is_unique_for_duplicate_or_absent_author_ids():
    assert relation_identity(0, {"id": "same"}) == "relation:0:same"
    assert relation_identity(1, {"id": "same"}) == "relation:1:same"
    assert relation_identity(2, {}) == "relation:2"
