"""Tool abstractions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Protocol

from miniagent.config.schema import AgentConfig


@dataclass
class ToolContext:
    """Runtime context passed to tools."""

    config: AgentConfig
    extras: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResult:
    """Structured result returned by a tool."""

    ok: bool
    content: str
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_message_content(self, max_chars: int) -> str:
        prefix = "OK" if self.ok else "ERROR"
        body = self.content if self.ok else (self.error or self.content)
        if len(body) > max_chars:
            body = body[:max_chars] + "\n...[truncated]"
        return f"{prefix}: {body}"


class Tool(Protocol):
    name: str
    description: str
    parameters_schema: Dict[str, Any]

    def run(self, arguments: Dict[str, Any], context: ToolContext) -> ToolResult:
        """Run the tool."""


def chat_completion_tool_schema(tool: Tool) -> Dict[str, Any]:
    """Convert a tool into Chat Completions tool schema."""

    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters_schema,
        },
    }
