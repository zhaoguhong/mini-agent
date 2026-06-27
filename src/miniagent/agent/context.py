"""Agent runtime context."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from miniagent.config.schema import AgentConfig
from miniagent.memory.session import SessionMemory
from miniagent.tools.registry import ToolRegistry


@dataclass
class AgentRuntime:
    """Shared runtime objects for an agent session."""

    config: AgentConfig
    memory: SessionMemory
    tools: ToolRegistry
    extras: Dict[str, Any] = field(default_factory=dict)

