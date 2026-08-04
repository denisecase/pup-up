"""Command modules for pup-up.

Each command module exposes a stable run(...) -> int entry point.

The CLI parser lives in pup_up.cli.
Behavior lives here.
"""

from pup_up.commands import todo, update

__all__ = ["todo", "update"]
