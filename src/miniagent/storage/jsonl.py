"""JSONL storage helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from miniagent.storage.paths import ensure_dir


def append_jsonl(path: Path, item: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(item, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                rows.append(json.loads(line))
    return rows

