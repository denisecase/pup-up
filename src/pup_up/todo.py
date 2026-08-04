"""Human action reporting."""

from importlib.resources import files
import tomllib
from typing import TypedDict, cast

from pup_up.types import RepositoryContext, TodoReport

__all__ = ["build_todo_report", "print_todo_report"]


TODO_CONFIG_PACKAGE = "pup_up.data"
TODO_CONFIG_NAME = "todo-surfaces.toml"


class TodoConfig(TypedDict):
    """Validated TODO configuration."""

    review_paths: dict[str, list[str]]
    confirmations: dict[str, list[str]]


def build_todo_report(target: RepositoryContext) -> TodoReport:
    """Build a repo-specific human review TODO report."""
    config = _load_todo_config()
    buckets = _todo_buckets(target)

    review_paths: list[str] = []
    confirmations: list[str] = []

    for bucket in buckets:
        review_paths.extend(config["review_paths"].get(bucket, []))
        confirmations.extend(config["confirmations"].get(bucket, []))

    return TodoReport(
        target=target,
        review_paths=tuple(_dedupe(review_paths)),
        confirmations=tuple(_dedupe(confirmations)),
    )


def print_todo_report(report: TodoReport) -> None:
    """Print a human review TODO report."""
    print(f"PROJECT TODO: {report.target.repo_name}")  # noqa: T201
    print("")  # noqa: T201

    print("Review repo-specific surfaces:")  # noqa: T201
    for path in report.review_paths:
        print(f"  {path}")  # noqa: T201

    print("")  # noqa: T201
    print("Confirm:")  # noqa: T201
    for item in report.confirmations:
        print(f"  {item}")  # noqa: T201


def _load_todo_config() -> TodoConfig:
    """Load and validate packaged TODO surface configuration."""
    config_path = files(TODO_CONFIG_PACKAGE).joinpath(TODO_CONFIG_NAME)
    config = cast(
        "dict[object, object]", tomllib.loads(config_path.read_text(encoding="utf-8"))
    )

    review_paths = _string_list_table(config.get("review_paths"), "review_paths")
    confirmations = _string_list_table(config.get("confirmations"), "confirmations")

    return {
        "review_paths": review_paths,
        "confirmations": confirmations,
    }


def _string_list_table(value: object, table_name: str) -> dict[str, list[str]]:
    """Validate a TOML table whose values are string lists."""
    if not isinstance(value, dict):
        msg = f"TODO config [{table_name}] must be a table."
        raise TypeError(msg)

    raw_table = cast("dict[object, object]", value)
    result: dict[str, list[str]] = {}

    for raw_key, raw_items in raw_table.items():
        if not isinstance(raw_key, str):
            msg = f"TODO config [{table_name}] keys must be strings."
            raise TypeError(msg)

        if not isinstance(raw_items, list):
            msg = f"TODO config [{table_name}.{raw_key}] must be a list."
            raise TypeError(msg)

        raw_list = cast("list[object]", raw_items)

        items: list[str] = []
        for item in raw_list:
            if not isinstance(item, str):
                msg = f"TODO config [{table_name}.{raw_key}] must contain only strings."
                raise TypeError(msg)

            items.append(item)

        result[raw_key] = items

    return result


def _todo_buckets(target: RepositoryContext) -> list[str]:
    """Return TODO buckets that apply to this repository."""
    buckets = ["default"]

    if "pyproject.toml" in target.files:
        buckets.append("pyproject")

    if any(path.startswith("src/") for path in target.files):
        buckets.append("python_src")

    if "zensical.toml" in target.files or "ALL-PY-SRC" in target.layers:
        buckets.append("zensical")

    if "package.json" in target.files:
        buckets.append("node")

    if any(path.startswith("notebooks/") for path in target.files):
        buckets.append("notebooks")

    if any(path.startswith("sql/") for path in target.files):
        buckets.append("sql")

    if any(path.startswith("data/raw/") for path in target.files):
        buckets.append("raw_data")

    return buckets


def _dedupe(items: list[str]) -> list[str]:
    """Deduplicate while preserving order."""
    seen: set[str] = set()
    result: list[str] = []

    for item in items:
        if item in seen:
            continue

        seen.add(item)
        result.append(item)

    return result
