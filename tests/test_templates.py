from pathlib import Path

from pup_up.detect import _detect_src_package
from pup_up.render import render_template
from pup_up.types import RepositoryContext


def test_detect_src_package_finds_package(tmp_path: Path) -> None:
    """src_package is inferred from src/__init__.py."""
    (tmp_path / "src" / "mypkg").mkdir(parents=True)
    (tmp_path / "src" / "mypkg" / "__init__.py").touch()
    result = _detect_src_package(tmp_path)
    assert result == "mypkg"


def test_detect_src_package_no_src(tmp_path: Path) -> None:
    """Returns empty string when no src/ exists."""
    result = _detect_src_package(tmp_path)
    assert result == ""


def test_detect_src_package_no_init(tmp_path: Path) -> None:
    """Returns empty string when src/ exists but has no __init__.py."""
    (tmp_path / "src" / "mypkg").mkdir(parents=True)
    result = _detect_src_package(tmp_path)
    assert result == ""


def test_render_template_src_package(tmp_path: Path) -> None:
    """{{ src_package }} is substituted in rendered output."""
    ctx = RepositoryContext(
        root=tmp_path,
        github_handle="denisecase",
        repo_name="test-repo",
        repo_url="https://github.com/denisecase/test-repo",
        site_url="https://denisecase.github.io/test-repo/",
        src_package="mypkg",
        files=frozenset(),
        layers=(),
    )
    result = render_template("::: {{ src_package }}", ctx)
    assert result == "::: mypkg"
