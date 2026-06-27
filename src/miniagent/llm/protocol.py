"""LLM protocol helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ChatResponse:
    """A normalized Chat Completions response."""

    message: Dict[str, Any]


@dataclass
class StreamDelta:
    """A normalized streaming delta."""

    content: str = ""
    tool_calls: Optional[List[Dict[str, Any]]] = None
