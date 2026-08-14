"""Tests for update planning behavior."""

from types import SimpleNamespace
from typing import cast

from pup_core.base.types import RepositoryContext

import pup_up.sync.plan as plan_module
from pup_up.templates.fetch import TemplateFile, TemplateSnapshot


def test_plan_preserves_existing_zensical_nav(
    tmp_path,
    monkeypatch,
) -> None:
    """Existing Zensical nav must survive template updates."""
    existing_text = """[project]
site_name = "Old"

nav = [
    {"Home" = "index.md"},
    {"API" = "api.md"},
]
"""

    rendered_text = """[project]
site_name = "New"

# ------------------------------------------------------------
# Navigation
# ------------------------------------------------------------
# If no explicit navigation is provided,
# then folder-based navigation will be used automatically.
"""

    (tmp_path / "zensical.toml").write_text(existing_text, encoding="utf-8")

    monkeypatch.setattr(
        plan_module,
        "fetch_template_text",
        lambda **_: rendered_text,
    )
    monkeypatch.setattr(
        plan_module,
        "render_template",
        lambda text, target: text,
    )

    target = cast(
        RepositoryContext,
        SimpleNamespace(root=tmp_path),
    )
    template_file = TemplateFile(
        layer="ALL-PY",
        template_path="zensical.toml.template",
        target_path="zensical.toml",
    )

    planned = plan_module._plan_one_template_file(
        target=target,
        snapshot=cast(TemplateSnapshot, object()),
        template_file=template_file,
    )

    assert planned.status == "changed"
    assert planned.desired_text is not None
    assert 'site_name = "New"' in planned.desired_text
    assert 'site_name = "Old"' not in planned.desired_text

    assert (
        """nav = [
    {"Home" = "index.md"},
    {"API" = "api.md"},
]"""
        in planned.desired_text
    )


def test_plan_uses_rendered_zensical_when_existing_has_no_nav(
    tmp_path,
    monkeypatch,
) -> None:
    """Without existing nav, rendered Zensical template wins exactly."""
    existing_text = """[project]
site_name = "Old"
"""

    rendered_text = """[project]
site_name = "New"

# ------------------------------------------------------------
# Navigation
# ------------------------------------------------------------
# If no explicit navigation is provided,
# then folder-based navigation will be used automatically.
"""

    (tmp_path / "zensical.toml").write_text(existing_text, encoding="utf-8")

    monkeypatch.setattr(
        plan_module,
        "fetch_template_text",
        lambda **_: rendered_text,
    )
    monkeypatch.setattr(
        plan_module,
        "render_template",
        lambda text, target: text,
    )

    target = cast(
        RepositoryContext,
        SimpleNamespace(root=tmp_path),
    )
    template_file = TemplateFile(
        layer="ALL-PY",
        template_path="zensical.toml.template",
        target_path="zensical.toml",
    )

    planned = plan_module._plan_one_template_file(
        target=target,
        snapshot=cast(TemplateSnapshot, object()),
        template_file=template_file,
    )

    assert planned.status == "changed"
    assert planned.desired_text == rendered_text
