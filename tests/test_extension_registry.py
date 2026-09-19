from chrona.extension_registry import PackageRegistry, resolve_evaluation_packages
from chrona.validation import validate_project


def _manifest(package_id, version, dependencies=(), **extra):
    return {"packageId": package_id, "version": version, "source": {"provider": "registry", "identity": "approved"}, "contentIdentity": f"sha256:{package_id}-{version}", "requires": {"projectFormats": ["timeline/v0.1"]}, "dependencies": list(dependencies)} | extra


def _reference(manifest):
    return {key: manifest[key] for key in ("packageId", "version", "source", "contentIdentity")}


def test_registry_resolves_only_trusted_pinned_declarative_dependency_closure():
    base = _manifest("base", "1.0.0")
    package = _manifest("semiconductor", "2.1.0", [_reference(base)])
    result = PackageRegistry({("registry", "approved")}, [package, base]).resolve(_reference(package), "timeline/v0.1")
    assert result.state == "verified"
    assert [item["packageId"] for item in result.manifests] == ["base", "semiconductor"]


def test_registry_rejects_missing_cycle_incompatible_and_executable_packages():
    missing = {"packageId": "none", "version": "1.0.0", "source": {}, "contentIdentity": "sha256:none"}
    assert PackageRegistry(set(), []).resolve(missing, "timeline/v0.1").diagnostics == ("E_PACKAGE_MISSING",)
    alpha = _manifest("alpha", "1.0.0"); beta = _manifest("beta", "1.0.0")
    alpha["dependencies"] = [_reference(beta)]; beta["dependencies"] = [_reference(alpha)]
    registry = PackageRegistry({("registry", "approved")}, [alpha, beta])
    assert registry.resolve(_reference(alpha), "timeline/v0.1").diagnostics == ("E_PACKAGE_DEPENDENCY_CYCLE",)
    bad_format = _manifest("other", "1.0.0", requires={"projectFormats": ["timeline/v0.2"]})
    assert PackageRegistry({("registry", "approved")}, [bad_format]).resolve(_reference(bad_format), "timeline/v0.1").diagnostics == ("E_PACKAGE_INCOMPATIBLE",)
    executable = _manifest("bad", "1.0.0", executableEntry="plugin.js")
    assert PackageRegistry({("registry", "approved")}, [executable]).resolve(_reference(executable), "timeline/v0.1").diagnostics == ("E_PACKAGE_EXECUTABLE_CONTENT",)


def test_registry_closure_is_an_explicit_validation_input_not_a_project_rewrite():
    package = _manifest("semiconductor", "2.1.0")
    registry = PackageRegistry({("registry", "approved")}, [package])
    manifests, diagnostics = resolve_evaluation_packages(registry, [_reference(package)], "timeline/v0.1")
    assert manifests == {"semiconductor": package} and diagnostics == ()
    project = {"version": "timeline/v0.1", "project": {"id": "p"}, "objects": {}, "relations": []}
    assert validate_project(project, package_registry=registry, package_references=[_reference(package)]) == []
