"""Tests for the update command."""

from pathlib import Path

from pytest import CaptureFixture

from pup_up.commands import update


def test_update_command_dry_run_with_local_templates(
    tmp_path: Path,
    capsys: CaptureFixture[str],
) -> None:
    """The update command should plan managed files without writing in dry-run mode."""
    repo = tmp_path / "example-python-repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "src").mkdir()
    (repo / "pyproject.toml").write_text(
        """
[project]
name = "example-python-repo"
version = "0.1.0"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    templates = tmp_path / "templates"
    (templates / "ALL").mkdir(parents=True)
    (templates / "ALL-PY").mkdir(parents=True)
    (templates / "ALL-PY-SRC").mkdir(parents=True)

    (templates / "ALL" / ".editorconfig").write_text(
        "root = true\n",
        encoding="utf-8",
    )
    (templates / "ALL-PY" / ".pre-commit-config.yaml").write_text(
        "repos: []\n",
        encoding="utf-8",
    )
    (templates / "ALL-PY" / "zensical.toml.template").write_text(
        'repo = "{{github_handle}}/{{ repo_name }}"\nsite = "{{ site_url }}"\n',
        encoding="utf-8",
    )

    exit_code = update.run(
        root=repo,
        write=False,
        templates="pup-pack/templates",
        ref="main",
        templates_path=templates,
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "[pup-up] DRY RUN" in captured.out
    assert "[pup-up] repo: example-python-repo" in captured.out
    assert "[pup-up] layers: ALL -> ALL-PY -> ALL-PY-SRC" in captured.out
    assert "WOULD ADD     .editorconfig [ALL]" in captured.out
    assert "WOULD ADD     .pre-commit-config.yaml [ALL-PY]" in captured.out
    assert "WOULD ADD     zensical.toml [ALL-PY]" in captured.out

    assert not (repo / ".editorconfig").exists()
    assert not (repo / ".pre-commit-config.yaml").exists()
    assert not (repo / "zensical.toml").exists()


def test_update_command_layer_override_uses_later_layer(
    tmp_path: Path,
    capsys: CaptureFixture[str],
) -> None:
    """Later additive layers should override earlier managed files."""
    repo = tmp_path / "example-python-repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "pyproject.toml").write_text(
        """
[project]
name = "example-python-repo"
version = "0.1.0"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    templates = tmp_path / "templates"
    (templates / "ALL").mkdir(parents=True)
    (templates / "ALL-PY").mkdir(parents=True)
    (templates / "ALL-PY-SRC").mkdir(parents=True)

    (templates / "ALL" / ".pre-commit-config.yaml").write_text(
        "repos: []\n",
        encoding="utf-8",
    )
    (templates / "ALL-PY" / ".pre-commit-config.yaml").write_text(
        "repos:\n  - repo: python-layer\n",
        encoding="utf-8",
    )

    exit_code = update.run(
        root=repo,
        write=True,
        templates_path=templates,
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "ADDED         .pre-commit-config.yaml [ALL-PY]" in captured.out
    assert (repo / ".pre-commit-config.yaml").read_text(encoding="utf-8") == (
        "repos:\n  - repo: python-layer\n"
    )


def test_update_command_reports_current_file(
    tmp_path: Path,
    capsys: CaptureFixture[str],
) -> None:
    """The update command should report current files when content already matches."""
    repo = tmp_path / "example-python-repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "pyproject.toml").write_text(
        """
[project]
name = "example-python-repo"
version = "0.1.0"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (repo / ".editorconfig").write_text("root = true\n", encoding="utf-8")

    templates = tmp_path / "templates"
    (templates / "ALL").mkdir(parents=True)
    (templates / "ALL-PY").mkdir(parents=True)
    (templates / "ALL-PY-SRC").mkdir(parents=True)

    (templates / "ALL" / ".editorconfig").write_text(
        "root = true\n",
        encoding="utf-8",
    )

    exit_code = update.run(
        root=repo,
        write=False,
        templates_path=templates,
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "CURRENT       .editorconfig [ALL]" in captured.out
