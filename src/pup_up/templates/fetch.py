"""Template source access."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
import io
from pathlib import Path
import tarfile
from tempfile import TemporaryDirectory
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from pup_up.base.errors import TemplateFetchError

__all__ = [
    "TemplateFile",
    "TemplateSnapshot",
    "TemplateSource",
    "fetch_template_snapshot",
    "fetch_template_text",
    "list_template_files",
]


@dataclass(frozen=True)
class TemplateFile:
    """One file discovered in a template layer."""

    layer: str
    template_path: str
    target_path: str


@dataclass(frozen=True)
class TemplateSnapshot:
    """Resolved template tree read from one local root.

    A snapshot is the single source everything reads from during a run. It is
    produced once by ``fetch_template_snapshot`` and points at either an
    extracted archive or an explicit local templates path.
    """

    root: Path
    repository: str
    ref: str
    from_local: bool


@dataclass(frozen=True)
class TemplateSource:
    """Canonical template source."""

    repository: str = "pup-pack/templates"
    ref: str = "main"
    local_path: Path | None = None


@contextmanager
def fetch_template_snapshot(*, source: TemplateSource) -> Iterator[TemplateSnapshot]:
    """Resolve a template source to a single local snapshot for the run.

    If ``source.local_path`` is set, the snapshot wraps that path directly and
    nothing is downloaded. Otherwise the template repository archive is fetched
    once for ``source.ref`` and extracted to a temporary directory that is
    removed when the context exits.

    Args:
        source: Template source.

    Yields:
        A snapshot rooted at a local template tree.

    Raises:
        TemplateFetchError: If the archive cannot be downloaded or extracted.
    """
    if source.local_path is not None:
        yield TemplateSnapshot(
            root=source.local_path.expanduser().resolve(),
            repository=source.repository,
            ref=source.ref,
            from_local=True,
        )
        return

    with TemporaryDirectory(prefix="pup-up-templates-") as raw_dest:
        root = _download_and_extract_snapshot(
            repository=source.repository,
            ref=source.ref,
            dest=Path(raw_dest),
        )
        yield TemplateSnapshot(
            root=root,
            repository=source.repository,
            ref=source.ref,
            from_local=False,
        )


def fetch_template_text(
    *,
    snapshot: TemplateSnapshot,
    template_file: TemplateFile,
) -> str | None:
    """Read one template file from the snapshot.

    The file's real ``template_path`` was already resolved by
    ``list_template_files``, so this is a direct local read with no suffix
    guessing.

    Args:
        snapshot: Resolved template snapshot.
        template_file: Discovered template file to read.

    Returns:
        File text, or None if the template file does not exist.

    Raises:
        TemplateFetchError: If the file exists but cannot be read.
    """
    path = snapshot.root / template_file.layer / template_file.template_path

    if not path.exists() or path.is_dir():
        return None

    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise TemplateFetchError(f"Could not read template file: {path}") from exc


def list_template_files(
    *,
    snapshot: TemplateSnapshot,
    layers: list[str],
) -> list[TemplateFile]:
    """List managed template files for selected layers.

    Later layers override earlier layers by target path.
    """
    discovered = _list_template_files(root=snapshot.root, layers=layers)

    by_target: dict[str, TemplateFile] = {}
    for item in discovered:
        by_target[item.target_path] = item

    return list(by_target.values())


def _list_template_files(
    *,
    root: Path,
    layers: list[str],
) -> list[TemplateFile]:
    """List template files from a local template tree."""
    resolved_root = root.expanduser().resolve()
    items: list[TemplateFile] = []

    for layer in layers:
        layer_root = resolved_root / layer
        if not layer_root.exists():
            continue

        for template_path in sorted(layer_root.rglob("*")):
            if not template_path.is_file():
                continue

            relative_path = template_path.relative_to(layer_root).as_posix()
            if _should_skip_template_path(relative_path):
                continue

            items.append(
                TemplateFile(
                    layer=layer,
                    template_path=relative_path,
                    target_path=_target_path_for_template_path(relative_path),
                )
            )

    return items


def _download_and_extract_snapshot(
    *,
    repository: str,
    ref: str,
    dest: Path,
) -> Path:
    """Download and extract the template repository archive once."""
    encoded_ref = quote(ref, safe="/")
    url = f"https://codeload.github.com/{repository}/tar.gz/{encoded_ref}"

    archive_bytes = _fetch_archive_bytes(url)

    try:
        with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as archive:
            archive.extractall(path=dest, filter="data")
    except (tarfile.TarError, OSError) as exc:
        raise TemplateFetchError(f"Could not extract template snapshot: {url}") from exc

    return _snapshot_root(dest=dest, url=url)


def _snapshot_root(*, dest: Path, url: str) -> Path:
    """Return the single top-level directory GitHub archives wrap content in."""
    directories = [entry for entry in dest.iterdir() if entry.is_dir()]

    if len(directories) != 1:
        raise TemplateFetchError(f"Unexpected template snapshot layout: {url}")

    return directories[0]


def _fetch_archive_bytes(url: str) -> bytes:
    """Fetch archive bytes from a trusted GitHub archive host."""
    parsed = urlparse(url)

    if parsed.scheme != "https":
        raise TemplateFetchError(f"Invalid URL scheme: {url}")

    if parsed.netloc != "codeload.github.com":
        raise TemplateFetchError(f"Invalid template host: {url}")

    request = Request(  # noqa: S310
        url,
        headers={
            "User-Agent": "pup-up",
        },
    )

    try:
        with urlopen(request, timeout=60) as response:  # noqa: S310
            return response.read()
    except HTTPError as exc:
        raise TemplateFetchError(
            f"Could not download template snapshot: {url}"
        ) from exc
    except URLError as exc:
        raise TemplateFetchError(
            f"Could not download template snapshot: {url}"
        ) from exc


def _target_path_for_template_path(path: str) -> str:
    """Convert a template path to a target repository path."""
    if path.endswith(".template"):
        return path.removesuffix(".template")

    return path


def _should_skip_template_path(path: str) -> bool:
    """Return whether a template path is internal or unsupported."""
    if not path:
        return True

    if path.startswith((".pup-up/", "__pycache__/")):
        return True

    if Path(path).name == ".DS_Store":
        return True

    return path.endswith(".pyc")
