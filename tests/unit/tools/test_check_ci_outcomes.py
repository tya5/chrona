from tools.check_ci_outcomes import assess


def test_ci_outcomes_accept_successful_required_and_dependent_steps():
    assert assess(required=(("conformance", "success"), ("pytest", "success")),
                  dependent=(("wheel", "success"),)) == ()


def test_ci_outcomes_reports_required_failure_and_required_dependent_skip():
    assert assess(required=(("conformance", "failure"), ("pytest", "success")),
                  dependent=(("wheel", "skipped"),)) == ("E_CI_REQUIRED_STEP:conformance:failure",)


def test_ci_outcomes_rejects_dependent_execution_after_failed_prerequisite():
    assert assess(required=(("conformance", "failure"),), dependent=(("wheel", "success"),)) == (
        "E_CI_REQUIRED_STEP:conformance:failure",
        "E_CI_DEPENDENT_STEP:wheel:success:expected=skipped",
    )
