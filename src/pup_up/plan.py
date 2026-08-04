"""Build, print, and apply update plans."""

from pathlib import Path

from pup_up.errors import UnsafePathError
from pup_up.fetch import (
    TemplateFile,
    TemplateSource,
    fetch_template_text,
    list_template_files,
)
from pup_up.render import render_template
from pup_up.types import FileStatus, PlannedFile, RepositoryContext, UpdatePlan

__all__ = [
    "build_update_plan",
    "print_update_plan",
    "write_update_plan",
]


def build_update_plan(
    *,
    target: RepositoryContext,
    source: TemplateSource,
    protected_paths: frozenset[str] = frozenset(),
) -> UpdatePlan:
    """Build an update plan from discovered template files."""
    planned_files: list[PlannedFile] = []

    template_files = list_template_files(
        source=source,
        layers=list(target.layers),
    )

    for template_file in template_files:
        planned_files.append(
            _plan_one_template_file(
                target=target,
                source=source,
                template_file=template_file,
            )
        )

    return UpdatePlan(
        target=target,
        files=tuple(planned_files),
    )


def print_update_plan(plan: UpdatePlan, *, write: bool) -> None:
    """Print a human-readable update plan."""
    mode = "WRITE" if write else "DRY RUN"

    print(f"[pup-up] {mode}")  # noqa: T201
    print(f"[pup-up] repo: {plan.target.repo_name}")  # noqa: T201
    print(f"[pup-up] root: {plan.target.root}")  # noqa: T201
    print(f"[pup-up] layers: {' -> '.join(plan.target.layers)}")  # noqa: T201
    print("")  # noqa: T201

    counts = _status_counts(plan)

    print("[pup-up] managed files")  # noqa: T201
    for file in plan.files:
        status = _status_label(file.status, write=write)
        source_label = f" [{file.source_layer}]" if file.source_layer else ""
        print(f"{status:13} {file.path.as_posix()}{source_label}")  # noqa: T201

    print("")  # noqa: T201
    print(  # noqa: T201
        "[pup-up] summary: "
        f"{counts['current']} current, "
        f"{counts['changed']} changed, "
        f"{counts['missing']} missing, "
        f"{counts['no-template']} no-template, "
        f"{counts['protected']} protected"
    )

    if not write:
        print("")  # noqa: T201
        print("[pup-up] no files written; rerun with --write to apply managed changes")  # noqa: T201


def write_update_plan(plan: UpdatePlan) -> None:
    """Write changed or missing managed files."""
    for file in plan.files:
        if file.status not in {"changed", "missing"}:
            continue

        if file.desired_text is None:
            continue

        target_path = _safe_target_path(plan.target.root, file.path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(file.desired_text, encoding="utf-8")


def _plan_one_template_file(
    *,
    target: RepositoryContext,
    source: TemplateSource,
    template_file: TemplateFile,
) -> PlannedFile:
    """Plan one discovered template file."""
    template_text = fetch_template_text(
        source=source,
        layer=template_file.layer,
        path=template_file.target_path,
    )

    if template_text is None:
        return PlannedFile(
            path=Path(template_file.target_path),
            status="no-template",
            source_layer=template_file.layer,
            source_path=f"{template_file.layer}/{template_file.template_path}",
            current_text=_read_current_text(
                target.root, Path(template_file.target_path)
            ),
            desired_text=None,
        )

    desired_text = render_template(template_text, target)
    relative_path = Path(template_file.target_path)
    current_text = _read_current_text(target.root, relative_path)

    status = _file_status(
        current_text=current_text,
        desired_text=desired_text,
    )

    return PlannedFile(
        path=relative_path,
        status=status,
        source_layer=template_file.layer,
        source_path=f"{template_file.layer}/{template_file.template_path}",
        current_text=current_text,
        desired_text=desired_text,
    )


def _file_status(
    *,
    current_text: str | None,
    desired_text: str,
) -> FileStatus:
    """Determine planned file status."""
    if current_text is None:
        return "missing"

    if current_text == desired_text:
        return "current"

    return "changed"


def _read_current_text(root: Path, path: Path) -> str | None:
    """Read current file text if present."""
    target_path = _safe_target_path(root, path)

    if not target_path.exists() or target_path.is_dir():
        return None

    try:
        return target_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None


def _safe_target_path(root: Path, path: Path) -> Path:
    """Resolve a path under the repository root."""
    target_path = (root / path).resolve()
    root_resolved = root.resolve()

    if target_path != root_resolved and root_resolved not in target_path.parents:
        raise UnsafePathError(target_path)

    return target_path


def _status_counts(plan: UpdatePlan) -> dict[FileStatus, int]:
    """Count file statuses."""
    counts: dict[FileStatus, int] = {
        "current": 0,
        "changed": 0,
        "missing": 0,
        "no-template": 0,
        "protected": 0,
    }

    for file in plan.files:
        counts[file.status] += 1

    return counts


def _status_label(status: FileStatus, *, write: bool) -> str:
    """Return display label for a file status."""
    match status:
        case "current":
            return "CURRENT"
        case "changed":
            return "CHANGED" if write else "WOULD CHANGE"
        case "missing":
            return "ADDED" if write else "WOULD ADD"
        case "no-template":
            return "NO TEMPLATE"
        case "protected":
            return "PROTECTED"
