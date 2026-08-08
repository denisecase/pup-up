"""Build and apply update plans."""

from collections.abc import Sequence
from pathlib import Path

from pup_up.base.errors import UnsafePathError
from pup_up.base.types import FileStatus, PlannedFile, RepositoryContext, UpdatePlan
from pup_up.templates.fetch import (
    TemplateFile,
    TemplateSource,
    fetch_template_text,
    list_template_files,
)
from pup_up.templates.render import render_template

__all__ = [
    "build_update_plan",
    "filter_update_plan",
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


def filter_update_plan(
    plan: UpdatePlan,
    selected_paths: Sequence[Path],
) -> UpdatePlan:
    """Return an update plan containing only selected managed files.

    Args:
        plan: Complete update plan.
        selected_paths: Repository-relative managed file paths to retain.

    Returns:
        Filtered update plan.

    Raises:
        ValueError: If a selected path is absolute, escapes the repository,
            or is not included in the managed update plan.
    """
    normalized_selected: set[str] = set()

    for path in selected_paths:
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(
                f"Selected path must be repository-relative and safe: {path}"
            )

        normalized_selected.add(path.as_posix())

    managed_paths = {file.path.as_posix() for file in plan.files}
    unknown_paths = normalized_selected - managed_paths

    if unknown_paths:
        paths = ", ".join(sorted(unknown_paths))
        raise ValueError(f"Selected path is not managed by pup-up: {paths}")

    filtered_files = tuple(
        file for file in plan.files if file.path.as_posix() in normalized_selected
    )

    return UpdatePlan(
        target=plan.target,
        files=filtered_files,
    )


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
