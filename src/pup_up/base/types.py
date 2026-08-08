"""Typed records for pup-up synchronization."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pup_core.base.types import RepositoryContext

__all__ = [
    "FileStatus",
    "PlannedFile",
    "UpdatePlan",
]

FileStatus = Literal[
    "current",
    "changed",
    "missing",
    "no-template",
    "protected",
]


@dataclass(frozen=True)
class PlannedFile:
    """A single managed file considered by pup-up."""

    path: Path
    status: FileStatus
    source_layer: str | None
    source_path: str | None
    current_text: str | None
    desired_text: str | None


@dataclass(frozen=True)
class UpdatePlan:
    """Complete update plan for a target repository."""

    target: RepositoryContext
    layers: tuple[str, ...]
    files: tuple[PlannedFile, ...]
