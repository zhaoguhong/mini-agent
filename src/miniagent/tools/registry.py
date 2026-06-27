"""Tool registry."""

from __future__ import annotations

from typing import Dict, Iterable, List

from miniagent.tools.base import Tool, chat_completion_tool_schema


class ToolRegistry:
    """A small registry for built-in and MCP tools."""

    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def extend(self, tools: Iterable[Tool]) -> None:
        for tool in tools:
            self.register(tool)

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"Unknown tool: {name}") from exc

    def names(self) -> List[str]:
        return sorted(self._tools)

    def schemas(self) -> List[dict]:
        return [chat_completion_tool_schema(self._tools[name]) for name in self.names()]

