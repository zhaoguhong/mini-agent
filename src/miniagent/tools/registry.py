"""Tool registry."""

from __future__ import annotations

from typing import Dict, Iterable, List

from miniagent.tools.base import Tool, chat_completion_tool_schema


class ToolRegistry:
    """A small registry for built-in and MCP tools."""

    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool by name."""

        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def extend(self, tools: Iterable[Tool]) -> None:
        """Register multiple tools."""

        for tool in tools:
            self.register(tool)

    def get(self, name: str) -> Tool:
        """Return a registered tool by name."""

        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"Unknown tool: {name}") from exc

    def names(self) -> List[str]:
        """Return registered tool names in stable order."""

        return sorted(self._tools)

    def schemas(self) -> List[dict]:
        """Return Chat Completions tool schemas for all tools."""

        return [chat_completion_tool_schema(self._tools[name]) for name in self.names()]
