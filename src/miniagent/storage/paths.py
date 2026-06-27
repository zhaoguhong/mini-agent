"""Path helpers."""

from __future__ import annotations

from pathlib import Path


def ensure_dir(path: Path) -> Path:
    """Create a directory when needed and return it."""

    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_workspace_path(workspace_root: Path, raw_path: str) -> Path:
    """Resolve a user path and ensure it remains inside the workspace."""

    root = workspace_root.expanduser().resolve()
    candidate = (root / raw_path).expanduser().resolve() if not Path(raw_path).is_absolute() else Path(raw_path).expanduser().resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("Path is outside workspace") from exc
    return candidate

