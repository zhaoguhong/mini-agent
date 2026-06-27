"""Agent event models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class AgentEvent:
    """A lifecycle event emitted by the agent."""

    type: str
    data: Dict[str, Any]

