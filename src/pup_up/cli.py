"""Command-line interface for pup-up.

This module parses arguments and dispatches commands.
Command behavior lives in pup_up.commands.

Commands:
uv run pup-up
uv run pup-up --write
uv run pup-up todo

Equivalent uvx usage after release:
uvx pup-up
uvx pup-up@latest
uvx pup-up --write
uvx pup-up todo
"""

import argparse
from collections.abc import Callable, Sequence
from pathlib import Path

from pup_up.commands import todo, update

__all__ = ["build_parser", "main"]

CommandFunc = Callable[[argparse.Namespace], int]

EXIT_OK = 0
EXIT_NO_COMMAND = 2


def _run_update(args: argparse.Namespace) -> int:
    """Bring the current repository up to the managed baseline."""
    return update.run(
        root=args.root,
        write=args.write,
        templates=args.templates,
        ref=args.ref,
        templates_path=args.templates_path,
    )


def _run_todo(args: argparse.Namespace) -> int:
    """Show repo-specific human work that pup-up cannot safely calculate."""
    return todo.run(root=args.root)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="pup-up",
        description=(
            "Bring the current repository up to the current Denise Case "
            "managed baseline from canonical templates."
        ),
    )

    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help=(
            "Repository root to update. Defaults to the nearest parent "
            "directory containing .git, or the current directory."
        ),
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help=(
            "Apply managed baseline changes. Without this flag, pup-up performs "
            "a dry run and reports what would change."
        ),
    )
    parser.add_argument(
        "--templates",
        default="denisecase/templates",
        help=(
            "GitHub owner/repo for canonical templates. "
            "Defaults to denisecase/templates."
        ),
    )
    parser.add_argument(
        "--ref",
        default="main",
        help="Git ref, branch, or tag to fetch templates from. Defaults to main.",
    )
    parser.add_argument(
        "--templates-path",
        type=Path,
        default=None,
        help=(
            "Optional local templates repository path. If provided, templates "
            "are read from disk instead of GitHub raw URLs."
        ),
    )

    subparsers = parser.add_subparsers(dest="command", required=False)

    # === TODO COMMAND ===

    todo_parser = subparsers.add_parser(
        "todo",
        help=(
            "Show repo-specific human review work that cannot be safely "
            "calculated or overwritten."
        ),
    )
    todo_parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help=(
            "Repository root to inspect. Defaults to the nearest parent "
            "directory containing .git, or the current directory."
        ),
    )
    todo_parser.set_defaults(func=_run_todo)

    parser.set_defaults(func=_run_update)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line interface.

    Args:
        argv: Optional command-line arguments. If None, uses sys.argv.

    Returns:
        Exit code from the executed command.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    func: CommandFunc | None = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return EXIT_NO_COMMAND

    return func(args)


if __name__ == "__main__":
    raise SystemExit(main())
