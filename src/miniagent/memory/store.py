"""Session persistence."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from miniagent.storage.jsonl import append_jsonl, read_jsonl
from miniagent.storage.paths import ensure_dir


class SessionStore:
    """Stores sessions as JSONL."""

    def __init__(self, sessions_dir: Path) -> None:
        self.sessions_dir = sessions_dir

    def save(self, messages: List[Dict[str, Any]], session_id: Optional[str] = None) -> str:
        """Save a session and return its session id."""

        ensure_dir(self.sessions_dir)
        active_id = session_id or str(uuid.uuid4())
        path = self.sessions_dir / f"{active_id}.jsonl"
        for message in messages:
            append_jsonl(path, message)
        return active_id

    def load(self, session_id: str) -> List[Dict[str, Any]]:
        """Load a saved session by id."""

        return list(read_jsonl(self.sessions_dir / f"{session_id}.jsonl"))
