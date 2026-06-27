"""Session memory."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class SessionMemory:
    """Stores the current conversation messages."""

    messages: List[Dict[str, Any]] = field(default_factory=list)

    def add(self, message: Dict[str, Any]) -> None:
        self.messages.append(message)

    def clear(self) -> None:
        self.messages.clear()

    def snapshot(self) -> List[Dict[str, Any]]:
        return [dict(message) for message in self.messages]

