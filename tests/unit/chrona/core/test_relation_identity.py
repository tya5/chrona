from chrona.core.relation_identity import relation_identities


def edge(*, relation_type="dependency", from_object="source", from_endpoint="end",
         to_object="target", to_endpoint="start", relation_id=None, lag="0d"):
    relation = {
        "type": relation_type,
        "from": {"object": from_object, "endpoint": from_endpoint},
        "to": {"object": to_object, "endpoint": to_endpoint},
        "lag": lag,
    }
    if relation_id is not None:
        relation["id"] = relation_id
    return relation


def test_unique_declared_id_is_encoded_and_survives_endpoint_or_lag_edits():
    first = edge(relation_id="a/b:%雪", from_object="source", lag="3wd")
    edited = edge(relation_id="a/b:%雪", from_object="other", to_endpoint="finish", lag="-2d")

    assert relation_identities((first,)) == ("relation:id:a%2Fb%3A%25%E9%9B%AA",)
    assert relation_identities((edited,)) == relation_identities((first,))


def test_fallback_identity_encodes_each_semantic_component_and_excludes_lag():
    relation = edge(relation_type="dep:weird", from_object="a:b", from_endpoint="e/end",
                    to_object="c%z", to_endpoint="雪", lag="4wd")
    changed_lag = edge(relation_type="dep:weird", from_object="a:b", from_endpoint="e/end",
                       to_object="c%z", to_endpoint="雪", lag="-1d")

    expected = "relation:edge:dep%3Aweird:a%3Ab:e%2Fend:c%25z:%E9%9B%AA"
    assert relation_identities((relation,)) == (expected,)
    assert relation_identities((changed_lag,)) == (expected,)


def test_fallback_distinguishes_type_and_each_endpoint_component():
    baseline = edge()
    variants = (
        edge(relation_type="blocks"),
        edge(from_object="other-source"),
        edge(from_endpoint="start"),
        edge(to_object="other-target"),
        edge(to_endpoint="end"),
    )

    identities = relation_identities((baseline, *variants))
    assert len(set(identities)) == len(identities)
    assert identities[0] == "relation:edge:dependency:source:end:target:start"


def test_unique_fallbacks_are_stable_when_unrelated_relations_are_removed_appended_or_reordered():
    first = edge(from_object="alpha", to_object="beta")
    second = edge(relation_type="blocks", from_object="gamma", to_object="delta")
    unrelated = edge(relation_type="relates", from_object="x", to_object="y")

    before = relation_identities((first, second, unrelated))
    after_removal = relation_identities((first, second))
    after_append = relation_identities((unrelated, first, second, edge(from_object="new")))
    after_reorder = relation_identities((second, first, unrelated))

    assert before[:2] == after_removal
    assert after_append[1:3] == after_removal
    assert after_reorder[:2] == (before[1], before[0])


def test_duplicate_and_empty_declared_ids_use_fallback_and_only_exact_duplicates_get_occurrences():
    duplicate_id_first = edge(relation_id="reused", from_object="a", to_object="b")
    duplicate_id_second = edge(relation_id="reused", from_object="c", to_object="d")
    empty_id = edge(relation_id="", from_object="empty", to_object="id")
    exact_first = edge(from_object="same", to_object="edge")
    exact_second = edge(from_object="same", to_object="edge")
    unique_id = edge(relation_id="unique", from_object="u", to_object="v")

    identities = relation_identities((duplicate_id_first, duplicate_id_second, empty_id,
                                       exact_first, exact_second, unique_id))

    assert identities == (
        "relation:edge:dependency:a:end:b:start",
        "relation:edge:dependency:c:end:d:start",
        "relation:edge:dependency:empty:end:id:start",
        "relation:edge:dependency:same:end:edge:start:occurrence:1",
        "relation:edge:dependency:same:end:edge:start:occurrence:2",
        "relation:id:unique",
    )


def test_encoded_declared_id_cannot_alias_fallback_namespace():
    declared = edge(relation_id="edge:dependency:source:end:target:start")
    fallback = edge()

    declared_identity, fallback_identity = relation_identities((declared, fallback))

    assert declared_identity == "relation:id:edge%3Adependency%3Asource%3Aend%3Atarget%3Astart"
    assert fallback_identity == "relation:edge:dependency:source:end:target:start"
    assert declared_identity != fallback_identity
