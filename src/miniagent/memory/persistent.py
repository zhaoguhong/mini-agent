"""Simple persistent memory."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from miniagent.storage.paths import ensure_dir


class PersistentMemory:
    """Reads and writes durable memory files."""

    def __init__(self, memory_dir: Path) -> None:
        self.memory_dir = memory_dir

    def load_summary(self) -> str:
        facts = self._load_json("facts.json")
        preferences = self._load_json("preferences.json")
        parts = []
        if facts:
            parts.append("Facts:\n" + json.dumps(facts, ensure_ascii=False, indent=2))
        if preferences:
            parts.append("Preferences:\n" + json.dumps(preferences, ensure_ascii=False, indent=2))
        return "\n\n".join(parts)

    def _load_json(self, name: str) -> Dict[str, Any]:
        path = self.memory_dir / name
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def save_json(self, name: str, data: Dict[str, Any]) -> None:
        ensure_dir(self.memory_dir)
        (self.memory_dir / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

