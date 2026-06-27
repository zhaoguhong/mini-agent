"""Small stdio MCP client wrapper."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List

from miniagent.config.schema import McpServerConfig


@dataclass
class McpToolInfo:
    """A tool exposed by an MCP server."""

    server: str
    name: str
    description: str
    input_schema: Dict[str, Any]


class McpClient:
    """Starts stdio MCP servers on demand."""

    def __init__(self, servers: List[McpServerConfig]) -> None:
        self.servers = servers

    def list_tools(self) -> List[McpToolInfo]:
        return asyncio.run(self._list_tools())

    def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> str:
        return asyncio.run(self._call_tool(server_name, tool_name, arguments))

    async def _list_tools(self) -> List[McpToolInfo]:
        tools: List[McpToolInfo] = []
        for server in self.servers:
            tools.extend(await self._list_server_tools(server))
        return tools

    async def _list_server_tools(self, server: McpServerConfig) -> List[McpToolInfo]:
        session, stdio_client, params_type = _import_mcp()
        params = params_type(command=server.command, args=server.args, env=server.env or None)
        async with stdio_client(params) as (read, write):
            async with session(read, write) as active:
                await active.initialize()
                response = await active.list_tools()
                return [
                    McpToolInfo(
                        server=server.name,
                        name=tool.name,
                        description=getattr(tool, "description", "") or "",
                        input_schema=getattr(tool, "inputSchema", {}) or {},
                    )
                    for tool in response.tools
                ]

    async def _call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> str:
        server = next((item for item in self.servers if item.name == server_name), None)
        if server is None:
            raise ValueError(f"Unknown MCP server: {server_name}")
        session, stdio_client, params_type = _import_mcp()
        params = params_type(command=server.command, args=server.args, env=server.env or None)
        async with stdio_client(params) as (read, write):
            async with session(read, write) as active:
                await active.initialize()
                result = await active.call_tool(tool_name, arguments)
                return _result_to_text(result)


def _import_mcp():
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
    except ModuleNotFoundError as exc:
        raise RuntimeError("The mcp package is required for MCP support.") from exc
    return ClientSession, stdio_client, StdioServerParameters


def _result_to_text(result: Any) -> str:
    parts = []
    for item in getattr(result, "content", []) or []:
        text = getattr(item, "text", None)
        if text is not None:
            parts.append(text)
        else:
            parts.append(str(item))
    return "\n".join(parts)

