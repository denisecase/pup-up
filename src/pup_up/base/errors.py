"""Exception types."""

from pup_core.base.errors import RepositoryDetectionError, UnsafePathError

__all__ = [
    "PupUpError",
    "RepositoryDetectionError",
    "TemplateFetchError",
    "UnsafePathError",
]


class PupUpError(Exception):
    """Base exception for pup-up."""


class TemplateFetchError(PupUpError):
    """Raised when template content cannot be fetched."""

    def __init__(self, message: str) -> None:
        """Initialize the error."""
        super().__init__(message)
