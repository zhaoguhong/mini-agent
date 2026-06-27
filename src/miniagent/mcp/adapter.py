"""Adapt MCP tools to mini-agent tools."""

from __future__ import annotations

from typing import Any, Dict, List

from miniagent.mcp.client import McpClient, McpToolInfo
from miniagent.tools.base import ToolContext, ToolResult


class McpToolAdapter:
    """A Tool wrapper around a remote MCP tool."""

    def __init__(self, client: McpClient, info: McpToolInfo) -> None:
        self.client = client
        self.info = info
        # Prefix names to avoid collisions between built-in tools and MCP tools.
        self.name = f"mcp__{info.server}__{info.name}"
        self.description = info.description or f"MCP tool {info.name} from {info.server}"
        self.parameters_schema = info.input_schema or {"type": "object", "properties": {}}

    def run(self, arguments: Dict[str, Any], context: ToolContext) -> ToolResult:
        """Call the remote MCP tool and normalize its result."""

        try:
            content = self.client.call_tool(self.info.server, self.info.name, arguments)
            return ToolResult(ok=True, content=content, metadata={"server": self.info.server, "tool": self.info.name})
        except Exception as exc:
            return ToolResult(ok=False, content="", error=str(exc), metadata={"server": self.info.server, "tool": self.info.name})


def load_mcp_tools(client: McpClient) -> List[McpToolAdapter]:
    """Discover MCP tools and return registry-ready adapters."""

    return [McpToolAdapter(client, info) for info in client.list_tools()]
