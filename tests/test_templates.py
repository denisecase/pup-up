from pathlib import Path

from pup_core.base.types import RepositoryContext

from pup_up.templates.render import render_template


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
    )
    result = render_template("::: {{ src_package }}", ctx)
    assert result == "::: mypkg"
