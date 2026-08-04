"""Exception types for pup-up."""

from pathlib import Path

__all__ = [
    "DcUpError",
    "RepositoryDetectionError",
    "TemplateFetchError",
    "UnsafePathError",
]


class DcUpError(Exception):
    """Base exception for pup-up."""


class RepositoryDetectionError(DcUpError):
    """Raised when pup-up cannot determine the target repository."""

    def __init__(self, message: str) -> None:
        """Initialize the error."""
        super().__init__(message)


class TemplateFetchError(DcUpError):
    """Raised when template content cannot be fetched."""

    def __init__(self, message: str) -> None:
        """Initialize the error."""
        super().__init__(message)


class UnsafePathError(DcUpError):
    """Raised when a path would escape the target repository."""

    def __init__(self, path: Path) -> None:
        """Initialize the error."""
        super().__init__(f"Unsafe path escapes repository root: {path}")
