"""Repository detection."""

import configparser
from pathlib import Path
import re

from pup_up.base.errors import RepositoryDetectionError
from pup_up.base.types import RepositoryContext
from pup_up.templates.baseline import infer_layers

__all__ = ["detect_repository"]


GITHUB_REMOTE_RE = re.compile(
    r"(?:git@github\.com:|https://github\.com/)"
    r"(?P<owner>[^/\s]+)/(?P<repo>[^/\s]+?)"
    r"(?:\.git)?/?$"
)


def detect_repository(root: Path | None = None) -> RepositoryContext:
    """Detect the repository context.

    Args:
        root: Optional repository root. If None, detect from current directory.

    Returns:
        Repository context.

    Raises:
        RepositoryDetectionError: If the target directory cannot be resolved.
    """
    local_repo_root_directory: Path = _resolve_repo_root(root)
    files = _snapshot_files(local_repo_root_directory)

    github_handle = _detect_github_handle(local_repo_root_directory) or "denisecase"
    repo_name = local_repo_root_directory.name

    repo_url = f"https://github.com/{github_handle}/{repo_name}"
    site_url = f"https://{github_handle}.github.io/{repo_name}/"
    src_package = _detect_src_package(local_repo_root_directory)

    layers = tuple(
        infer_layers(
            repo_root=local_repo_root_directory,
            repo_name=repo_name,
            files=files,
        )
    )

    return RepositoryContext(
        root=local_repo_root_directory,
        github_handle=github_handle,
        repo_name=repo_name,
        repo_url=repo_url,
        site_url=site_url,
        src_package=src_package,
        files=frozenset(files),
        layers=layers,
    )


def _resolve_repo_root(root: Path | None) -> Path:
    """Resolve the target repository root on the local file system.

    Args:
        root: Optional starting path. If None, use current working directory.

    Returns:
        Resolved repository root path, for example: C:/Repos/pup-up

    Raises:
        RepositoryDetectionError: If the target directory cannot be resolved.
    """
    start = Path.cwd() if root is None else root
    start = start.expanduser().resolve()

    if not start.exists():
        raise RepositoryDetectionError(f"Repository path does not exist: {start}")

    if start.is_file():
        start = start.parent

    for candidate in [start, *start.parents]:
        if (candidate / ".git").exists():
            return candidate

    return start


def _snapshot_files(root: Path) -> set[str]:
    """Return repository-relative file and directory markers.

    Args:
        root: Repository root directory.

    Returns:
        Set of repository-relative paths for all files and directories,
        for example: {
            "README.md", "src/", "src/pup_up/", "src/pup_up/detect.py"
        }
    """
    result: set[str] = set()

    ignored_dirs = {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "dist",
        "build",
        "htmlcov",
        "node_modules",
    }

    for path in root.rglob("*"):
        rel = path.relative_to(root).as_posix()

        if any(part in ignored_dirs for part in path.relative_to(root).parts):
            continue

        if path.is_dir():
            result.add(rel)
            result.add(f"{rel}/")
        else:
            result.add(rel)

    return result


def _detect_github_handle(root: Path) -> str | None:
    """Infer GitHub owner/handle from .git/config if possible.

    Args:
        root: Repository root directory.

    Returns:
        GitHub owner/handle if detected, otherwise None.
    """
    git_config = root / ".git" / "config"
    if not git_config.exists():
        return None

    parser = configparser.ConfigParser()
    try:
        parser.read(git_config, encoding="utf-8")
    except configparser.Error:
        return None

    section = 'remote "origin"'
    if not parser.has_section(section):
        return None

    url = parser.get(section, "url", fallback="")
    match = GITHUB_REMOTE_RE.search(url.strip())
    if match is None:
        return None

    return match.group("owner")


def _detect_src_package(root: Path) -> str:
    """Infer the primary package name from src/."""
    src = root / "src"
    if not src.exists():
        return ""
    for candidate in sorted(src.iterdir()):
        if candidate.is_dir() and (candidate / "__init__.py").exists():
            return candidate.name
    return ""
