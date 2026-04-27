from __future__ import annotations


def test_legacy_editor_dependency_is_not_exported() -> None:
    import app.api.deps as deps

    assert not hasattr(deps, "EditorServiceDep")
