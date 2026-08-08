"""Minimal template rendering."""

from pup_up.base.types import RepositoryContext

__all__ = ["render_template"]


def render_template(text: str, target: RepositoryContext) -> str:
    """Render simple repository identity tokens.

    This is deliberately not a full template engine.

    Args:
        text: Template text.
        target: Target repository context.

    Returns:
        Rendered text.
    """
    tokens = {
        "repo_name": target.repo_name,
        "github_handle": target.github_handle,
        "repo_url": target.repo_url,
        "site_url": target.site_url,
        "src_package": target.src_package,
    }

    rendered = text
    for name, value in tokens.items():
        rendered = rendered.replace(f"{{{{ {name} }}}}", value)
        rendered = rendered.replace(f"{{{{{name}}}}}", value)

    return rendered
