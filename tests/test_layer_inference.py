from pathlib import Path

from pup_up.templates.baseline import infer_layers


def test_inference_py_simple(tmp_path: Path):
    """Expectation: ALL, ALL-PY (Python project, no src folder)."""
    repo = tmp_path / "my-project"
    repo.mkdir()
    (repo / "pyproject.toml").touch()

    layers = infer_layers(
        repo_root=repo, repo_name="my-project", files={"pyproject.toml"}
    )
    assert layers == ["ALL", "ALL-PY"]


def test_inference_py_src_explicit(tmp_path: Path):
    """Expectation: ALL, ALL-PY, ALL-PY-SRC (Python project with src folder)."""
    repo = tmp_path / "my-project"
    repo.mkdir()
    (repo / "pyproject.toml").touch()
    (repo / "src").mkdir()

    layers = infer_layers(
        repo_root=repo, repo_name="my-project", files={"pyproject.toml"}
    )
    assert layers == ["ALL", "ALL-PY", "ALL-PY-SRC"]


def test_inference_typescript(tmp_path: Path):
    """Expectation: ALL, ALL-TS (TS project)."""
    repo = tmp_path / "my-ts-project"
    repo.mkdir()
    (repo / "package.json").touch()

    layers = infer_layers(
        repo_root=repo, repo_name="my-ts-project", files={"package.json"}
    )
    assert layers == ["ALL", "ALL-TS"]
