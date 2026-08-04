"""Baseline layer inference and managed file declarations."""

from pathlib import Path

__all__ = ["PRESERVE_PATTERNS", "infer_layers"]

PRESERVE_PATTERNS: tuple[str, ...] = (
    "README.md",
    "artifacts/**",
    "data/**",
    "docs/**",
    "notebooks/**",
    "sql/**",
    "src/**",
    "tests/**",
)


def infer_layers(*, repo_root: Path, repo_name: str, files: set[str]) -> list[str]:
    """Infer additive template layers based strictly on file existence."""
    # 1. Identify physical markers
    has_py = "pyproject.toml" in files
    has_src = (repo_root / "src").is_dir()
    is_ts = "package.json" in files

    # 2. Build Layers (Ordered by specificity)
    layers: list[str] = ["ALL"]

    # Base Tooling
    if has_py:
        layers.append("ALL-PY")
    elif is_ts:
        layers.append("ALL-TS")

    # Structural Overlays
    if has_py and has_src:
        layers.append("ALL-PY-SRC")

    return layers
