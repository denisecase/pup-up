"""Apply or preview the managed repository baseline."""

from pathlib import Path

from pup_up.detect import detect_repository
from pup_up.fetch import TemplateSource
from pup_up.plan import build_update_plan, print_update_plan, write_update_plan

__all__ = ["run"]


def run(
    *,
    root: Path | None = None,
    write: bool = False,
    templates: str = "denisecase/templates",
    ref: str = "main",
    templates_path: Path | None = None,
) -> int:
    """Preview or apply managed baseline updates.

    Args:
        root: Repository root. If None, pup-up detects the current repo root.
        write: Whether to write changes. False means dry-run only.
        templates: GitHub owner/repo for canonical templates.
        ref: Git ref, branch, or tag.
        templates_path: Optional local templates repo path.

    Returns:
        Process exit code.
    """
    repository = detect_repository(root)

    source = TemplateSource(
        repository=templates,
        ref=ref,
        local_path=templates_path,
    )

    plan = build_update_plan(
        target=repository,
        source=source,
        protected_paths=frozenset({"docs/api.md", "README.md"}),
    )

    print_update_plan(plan, write=write)

    if write:
        write_update_plan(plan)

    return 0
