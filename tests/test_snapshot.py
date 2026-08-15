"""Tests for template snapshot resolution."""

import io
from pathlib import Path
import tarfile
from urllib.request import Request

import pytest

from pup_up.base.errors import TemplateFetchError
from pup_up.templates import fetch
from pup_up.templates.fetch import (
    TemplateSource,
    fetch_template_snapshot,
    fetch_template_text,
    list_template_files,
)


def _make_archive(files: dict[str, str], *, prefix: str = "templates-abc123") -> bytes:
    """Build a GitHub-style tar.gz with a single top-level prefix directory."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for relative_path, text in files.items():
            data = text.encode("utf-8")
            info = tarfile.TarInfo(name=f"{prefix}/{relative_path}")
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def test_snapshot_from_local_does_not_download(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A local templates path yields a snapshot without any download."""

    def _fail(_url: str) -> bytes:
        raise AssertionError("archive download must not run for local sources")

    monkeypatch.setattr(fetch, "_fetch_archive_bytes", _fail)

    (tmp_path / "ALL").mkdir()
    (tmp_path / "ALL" / ".editorconfig").write_text("root = true\n", encoding="utf-8")

    source = TemplateSource(repository="pup-pack/templates", local_path=tmp_path)

    with fetch_template_snapshot(source=source) as snapshot:
        assert snapshot.from_local is True
        assert snapshot.root == tmp_path.expanduser().resolve()
        files = list_template_files(snapshot=snapshot, layers=["ALL"])

    assert [file.target_path for file in files] == [".editorconfig"]


def test_snapshot_downloads_once_and_strips_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A remote source resolves the ref to a SHA, downloads one archive, and
    reads from the stripped root."""
    resolved_sha = "a" * 40
    calls: list[str] = []

    def _fake_resolve(*, repository: str, ref: str) -> str:
        assert repository == "pup-pack/templates"
        assert ref == "v0.1.1"
        return resolved_sha

    def _fake_download(url: str) -> bytes:
        calls.append(url)
        return _make_archive(
            {
                "ALL/.editorconfig": "root = true\n",
                "ALL-PY/zensical.toml.template": 'repo = "{{ repo_name }}"\n',
            }
        )

    monkeypatch.setattr(fetch, "_resolve_ref_to_commit", _fake_resolve)
    monkeypatch.setattr(fetch, "_fetch_archive_bytes", _fake_download)

    source = TemplateSource(repository="pup-pack/templates", ref="v0.1.1")

    with fetch_template_snapshot(source=source) as snapshot:
        assert snapshot.from_local is False
        assert snapshot.ref == resolved_sha

        files = {
            file.target_path: file
            for file in list_template_files(snapshot=snapshot, layers=["ALL", "ALL-PY"])
        }
        snapshot_root = snapshot.root

        zensical = files["zensical.toml"]
        assert zensical.template_path == "zensical.toml.template"
        text = fetch_template_text(snapshot=snapshot, template_file=zensical)
        assert text == 'repo = "{{ repo_name }}"\n'

    assert len(calls) == 1
    assert calls[0].endswith(f"/tar.gz/{resolved_sha}")
    assert not snapshot_root.exists()


def test_snapshot_rejects_multiple_top_level_dirs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Extraction with more than one top-level dir is a snapshot error."""

    def _two_dirs(_url: str) -> bytes:
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
            for name in ("a/ALL/.editorconfig", "b/ALL/.editorconfig"):
                data = b"root = true\n"
                info = tarfile.TarInfo(name=name)
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
        return buffer.getvalue()

    monkeypatch.setattr(fetch, "_fetch_archive_bytes", _two_dirs)

    source = TemplateSource(repository="pup-pack/templates")

    with (
        pytest.raises(TemplateFetchError),
        fetch_template_snapshot(source=source) as _snapshot,
    ):
        pass


def test_fetch_template_text_returns_none_for_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A listed target with no backing file resolves to None."""

    def _fake_download(_url: str) -> bytes:
        return _make_archive({"ALL/.editorconfig": "root = true\n"})

    monkeypatch.setattr(fetch, "_fetch_archive_bytes", _fake_download)

    source = TemplateSource(repository="pup-pack/templates")
    missing = fetch.TemplateFile(
        layer="ALL",
        template_path="does-not-exist.toml",
        target_path="does-not-exist.toml",
    )

    with fetch_template_snapshot(source=source) as snapshot:
        assert fetch_template_text(snapshot=snapshot, template_file=missing) is None


def test_resolve_ref_short_circuits_full_sha(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A full 40-hex ref is already immutable: no API call is made."""

    def _no_network(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("must not hit the network for a full SHA")

    monkeypatch.setattr(fetch, "urlopen", _no_network)

    sha = "0123456789abcdef0123456789abcdef01234567"
    assert fetch._resolve_ref_to_commit(repository="pup-pack/templates", ref=sha) == sha


def test_resolve_ref_queries_api_for_branch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A branch name is resolved to a SHA via the commits API."""
    resolved = "b" * 40
    seen: dict[str, str] = {}

    class _Resp:
        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

        def read(self) -> bytes:
            return (resolved + "\n").encode("utf-8")  # trailing newline is stripped

    def _fake_urlopen(request: Request, timeout: int = 0) -> _Resp:
        seen["url"] = request.full_url
        return _Resp()

    monkeypatch.setattr(fetch, "urlopen", _fake_urlopen)

    got = fetch._resolve_ref_to_commit(repository="pup-pack/templates", ref="main")

    assert got == resolved
    assert seen["url"] == "https://api.github.com/repos/pup-pack/templates/commits/main"


def test_resolve_ref_rejects_non_sha_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A response that isn't a 40-hex SHA is a fetch error, not a bad URL."""

    class _Resp:
        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

        def read(self) -> bytes:
            return b"not-a-sha"

    monkeypatch.setattr(fetch, "urlopen", lambda *_a, **_k: _Resp())

    with pytest.raises(TemplateFetchError):
        fetch._resolve_ref_to_commit(repository="pup-pack/templates", ref="main")
