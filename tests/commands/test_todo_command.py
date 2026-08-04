"""Tests for the todo command."""

from pathlib import Path

from pytest import CaptureFixture

from pup_up.commands import todo


def test_todo_command_prints_basic_report(
    tmp_path: Path,
    capsys: CaptureFixture[str],
) -> None:
    """The todo command should print repo-specific review paths and confirmations."""
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

    exit_code = todo.run(root=repo)

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PROJECT TODO: example-python-repo" in captured.out
    assert "Review repo-specific surfaces:" in captured.out
    assert "  README.md" in captured.out
    assert "  docs/index.md" in captured.out
    assert "  pyproject.toml" in captured.out
    assert "Confirm:" in captured.out
    assert "  repo-specific project description is accurate" in captured.out
    assert "  package metadata is correct" in captured.out


def test_todo_command_adds_notebook_confirmation(
    tmp_path: Path,
    capsys: CaptureFixture[str],
) -> None:
    """The todo command should include notebook review when notebooks exist."""
    repo = tmp_path / "example-notebooks"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "notebooks").mkdir()
    (repo / "notebooks" / "analysis.ipynb").write_text(
        "{}\n",
        encoding="utf-8",
    )

    exit_code = todo.run(root=repo)

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PROJECT TODO: example-notebooks" in captured.out
    assert "  notebook execution state is intentional" in captured.out


def test_todo_command_adds_sql_confirmation(
    tmp_path: Path,
    capsys: CaptureFixture[str],
) -> None:
    """The todo command should include SQL review when SQL files exist."""
    repo = tmp_path / "example-sql"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "sql").mkdir()
    (repo / "sql" / "query.sql").write_text(
        "select 1;\n",
        encoding="utf-8",
    )

    exit_code = todo.run(root=repo)

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PROJECT TODO: example-sql" in captured.out
    assert "  SQL examples and database paths are current" in captured.out
