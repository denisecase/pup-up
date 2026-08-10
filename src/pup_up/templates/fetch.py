"""Template source access."""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import cast
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from pup_up.base.errors import TemplateFetchError

__all__ = [
    "TemplateFile",
    "TemplateSource",
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
class TemplateSource:
    """Canonical template source."""

    repository: str = "pup-pack/templates"
    ref: str = "main"
    local_path: Path | None = None


def fetch_template_text(
    *,
    source: TemplateSource,
    layer: str,
    path: str,
) -> str | None:
    """Fetch one template file.

    Args:
        source: Template source.
        layer: Template layer, such as ALL-PY.
        path: Repository-relative managed file path.

    Returns:
        File text, or None if the template file does not exist.

    Raises:
        TemplateFetchError: If fetching fails for a reason other than not found.
    """
    if source.local_path is not None:
        return _fetch_local_template_text(
            local_path=source.local_path,
            layer=layer,
            path=path,
        )

    return _fetch_github_template_text(
        repository=source.repository,
        ref=source.ref,
        layer=layer,
        path=path,
    )


def list_template_files(
    *,
    source: TemplateSource,
    layers: list[str],
) -> list[TemplateFile]:
    """List managed template files for selected layers.

    Later layers override earlier layers by target path.
    """
    discovered: list[TemplateFile]

    if source.local_path is not None:
        discovered = _list_local_template_files(
            local_path=source.local_path,
            layers=layers,
        )
    else:
        discovered = _list_github_template_files(
            repository=source.repository,
            ref=source.ref,
            layers=layers,
        )

    by_target: dict[str, TemplateFile] = {}
    for item in discovered:
        by_target[item.target_path] = item

    return list(by_target.values())


def _list_github_template_files(
    *,
    repository: str,
    ref: str,
    layers: list[str],
) -> list[TemplateFile]:
    """List template files from GitHub's recursive tree API."""
    encoded_ref = quote(ref, safe="")
    url = (
        f"https://api.github.com/repos/{repository}/git/trees/{encoded_ref}?recursive=1"
    )

    payload = _fetch_json_object(url)
    tree = payload.get("tree")

    if not isinstance(tree, list):
        raise TemplateFetchError(f"Unexpected GitHub tree response: {url}")

    selected_layers = set(layers)
    layer_order = {layer: index for index, layer in enumerate(layers)}
    items: list[TemplateFile] = []

    tree_entries = cast(list[object], tree)
    for entry in tree_entries:
        if not isinstance(entry, dict):
            continue

        entry_data = cast(dict[object, object], entry)

        if entry_data.get("type") != "blob":
            continue

        raw_path = entry_data.get("path")
        if not isinstance(raw_path, str):
            continue

        layer, relative_path = _split_layer_path(raw_path)

        if layer not in selected_layers:
            continue

        if _should_skip_template_path(relative_path):
            continue

        items.append(
            TemplateFile(
                layer=layer,
                template_path=relative_path,
                target_path=_target_path_for_template_path(relative_path),
            )
        )

    return sorted(
        items,
        key=lambda item: (layer_order[item.layer], item.target_path),
    )


def _list_local_template_files(
    *,
    local_path: Path,
    layers: list[str],
) -> list[TemplateFile]:
    """List template files from a local templates repository."""
    root = local_path.expanduser().resolve()
    items: list[TemplateFile] = []

    for layer in layers:
        layer_root = root / layer
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


def _fetch_local_template_text(
    *,
    local_path: Path,
    layer: str,
    path: str,
) -> str | None:
    """Fetch template text from a local templates repository."""
    template_path = local_path.expanduser().resolve() / layer / path

    if not template_path.exists():
        template_path_with_suffix = Path(f"{template_path}.template")
        if not template_path_with_suffix.exists():
            return None
        template_path = template_path_with_suffix

    if template_path.is_dir():
        return None

    try:
        return template_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise TemplateFetchError(
            f"Could not read template file: {template_path}"
        ) from exc


def _fetch_github_template_text(
    *,
    repository: str,
    ref: str,
    layer: str,
    path: str,
) -> str | None:
    """Fetch template text from GitHub raw content."""
    raw_path = f"{layer}/{path}"
    url = f"https://raw.githubusercontent.com/{repository}/{ref}/{raw_path}"

    text = _fetch_url_text(url)
    if text is not None:
        return text

    template_url = f"{url}.template"
    return _fetch_url_text(template_url)


def _fetch_url_text(url: str) -> str | None:
    """Fetch text from a trusted HTTPS URL, returning None for HTTP 404."""
    parsed = urlparse(url)

    if parsed.scheme != "https":
        raise TemplateFetchError(f"Invalid URL scheme: {url}")

    if parsed.netloc != "raw.githubusercontent.com":
        raise TemplateFetchError(f"Invalid template host: {url}")

    request = Request(  # noqa: S310
        url,
        headers={
            "User-Agent": "pup-up",
        },
    )

    try:
        with urlopen(request, timeout=20) as response:  # noqa: S310
            return response.read().decode("utf-8")
    except HTTPError as exc:
        if exc.code == 404:
            return None
        raise TemplateFetchError(f"Could not fetch template file: {url}") from exc
    except URLError as exc:
        raise TemplateFetchError(f"Could not fetch template file: {url}") from exc


def _fetch_json_object(url: str) -> dict[str, object]:
    """Fetch a trusted GitHub API JSON object."""
    parsed = urlparse(url)

    if parsed.scheme != "https":
        raise TemplateFetchError(f"Invalid URL scheme: {url}")

    if parsed.netloc != "api.github.com":
        raise TemplateFetchError(f"Invalid template API host: {url}")

    request = Request(  # noqa: S310
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "pup-up",
        },
    )

    try:
        with urlopen(request, timeout=20) as response:  # noqa: S310
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise TemplateFetchError(f"Could not list template files: {url}") from exc
    except URLError as exc:
        raise TemplateFetchError(f"Could not list template files: {url}") from exc
    except json.JSONDecodeError as exc:
        raise TemplateFetchError(f"Could not parse template file list: {url}") from exc

    if not isinstance(payload, dict):
        raise TemplateFetchError(f"Unexpected GitHub API response: {url}")

    return cast(dict[str, object], payload)


def _split_layer_path(path: str) -> tuple[str, str]:
    """Split a template repository path into layer and relative path."""
    parts = path.split("/", 1)
    if len(parts) != 2:
        return path, ""

    return parts[0], parts[1]


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
