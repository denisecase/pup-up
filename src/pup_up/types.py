"""Shared typed records."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

__all__ = [
    "FileStatus",
    "PlannedFile",
    "RepositoryContext",
    "TodoReport",
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
class RepositoryContext:
    """Detected information about the target repository."""

    root: Path
    github_handle: str
    repo_name: str
    repo_url: str
    site_url: str
    src_package: str
    files: frozenset[str]
    layers: tuple[str, ...]


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
    files: tuple[PlannedFile, ...]


@dataclass(frozen=True)
class TodoReport:
    """Human review TODO report for repo-specific work."""

    target: RepositoryContext
    review_paths: tuple[str, ...]
    confirmations: tuple[str, ...]
