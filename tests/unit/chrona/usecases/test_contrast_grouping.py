from chrona.presentation.scene.contrast_policy import EncodedFillPair, SceneContrastFinding
from chrona.presentation.style import EncodingSource, EncodingWitness
from chrona.usecases.contrast_grouping import group_contrast_findings


def _finding(identifier, *, scene="/surface", value="active", fill="#42314A", ground="#FFFFFF",
             ratio=3.0, code="W_SCENE_ENCODING_CONTRAST", severity="warning", witness=True, pair=True):
    encoding = (EncodingWitness("fill", "status", "status", value,
                                (EncodingSource("view", "view", "/color"),)) if witness else None)
    encoded_pair = (EncodedFillPair(fill, 1.0, fill, ground, ratio, 3.0) if pair else None)
    return SceneContrastFinding(code, severity, scene, "mark", "planned", identifier, ratio, 3.0,
                                "below-floor", "host", ground, "fill", encoding=encoding,
                                encoding_pair=encoded_pair)


def test_groups_only_same_realised_encoded_pair_in_stable_first_order():
    first = _finding("one")
    same = _finding("two")
    changed_value = _finding("three", value="blocked")
    changed_fill = _finding("four", fill="#51405A")
    changed_ground = _finding("five", ground="#000000")
    changed_ratio = _finding("six", ratio=2.9)
    other_surface = _finding("seven", scene="/another")

    groups = group_contrast_findings((first, same, changed_value, changed_fill, changed_ground,
                                      changed_ratio, other_surface))

    assert groups == ((first, same), (changed_value,), (changed_fill,), (changed_ground,),
                      (changed_ratio,), (other_surface,))


def test_nonwarning_missing_witness_or_missing_pair_findings_remain_singletons():
    findings = (
        _finding("error", severity="error"),
        _finding("info", code="I_SCENE_DECORATION_ABSENT", severity="info"),
        _finding("accepted", code="W_SCENE_CONTRAST_ACCEPTED"),
        _finding("unknown", code="W_SCENE_CONTRAST_GROUND_UNSUPPORTED", witness=False),
        _finding("no-witness", witness=False),
        _finding("no-pair", pair=False),
    )
    assert group_contrast_findings(findings) == tuple((finding,) for finding in findings)
