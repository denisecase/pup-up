"""Print repo-specific human review work for pup-up."""

from pathlib import Path

from pup_up.detect import detect_repository
from pup_up.todo import build_todo_report, print_todo_report

__all__ = ["run"]


def run(*, root: Path | None = None) -> int:
    """Show non-calculatable repo-specific work.

    Args:
        root: Repository root. If None, pup-up detects the current repo root.

    Returns:
        Process exit code.
    """
    repository = detect_repository(root)
    report = build_todo_report(repository)
    print_todo_report(report)
    return 0
