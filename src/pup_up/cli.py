"""Command-line interface for pup-up.

This module parses arguments and dispatches update behavior.

Commands:
uv run pup-up
uv run pup-up --write

Equivalent uvx usage after release:
uvx pup-up
uvx pup-up@latest
uvx pup-up --write
"""

import argparse
from collections.abc import Sequence
from pathlib import Path

from pup_up.commands import update

__all__ = ["build_parser", "main"]


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
        "--diff",
        action="store_true",
        help="Show unified diffs for managed files that would change.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help=(
            "Optional repository-relative managed file paths. "
            "When provided with --write, only these files are written."
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

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line interface.

    Args:
        argv: Optional command-line arguments. If None, uses sys.argv.

    Returns:
        Exit code from the update command.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    return update.run(
        root=args.root,
        write=args.write,
        show_diff=args.diff,
        selected_paths=args.paths,
        templates=args.templates,
        ref=args.ref,
        templates_path=args.templates_path,
    )


if __name__ == "__main__":
    raise SystemExit(main())
